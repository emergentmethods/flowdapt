import asyncio
from abc import ABC, abstractmethod
from signal import SIGINT, SIGTERM
from typing import Any, Type

from flowdapt.lib.context import ApplicationContext, create_context
from flowdapt.lib.logger import get_logger, log_once
from flowdapt.lib.utils.taskset import TaskSet


logger = get_logger(__name__)


class Service(ABC):
    def __init__(self, context: ApplicationContext, **kwargs) -> None:
        self._context = context
        self.__initialize__(**kwargs)

    def __initialize__(self, **kwargs):
        pass

    async def get_status(self):
        return {"status": "OK"}

    @abstractmethod
    async def __startup__(self, *args, **kwargs): ...

    @abstractmethod
    async def __shutdown__(self, *args, **kwargs): ...

    @abstractmethod
    async def __run__(self, *args, **kwargs): ...


def is_service(obj: Any):
    return issubclass(obj, Service)


class ServiceController:
    def __init__(
        self,
        context: ApplicationContext | dict[str, Any],
    ):
        self._context = create_context(context) if isinstance(context, dict) else context

        assert self._context.rpc, "ServiceController requires an RPC in the context"
        assert self._context.config, "ServiceController requires a Configuration in the context"

        self._loop = asyncio.get_running_loop()

        self._should_exit = False
        self._service_registry: set[Service] = set()
        self._service_task_set = TaskSet(logger=logger)
        self._task_sets: dict[str, TaskSet] = {}

        # Add the Service related objects needed in the context
        self._context.controller = self
        self._context.service_registry = self._service_registry
        self._context.task_set = self._service_task_set
        self._context.flags = {"services_ready": False}

        self._register_core_services()

    async def get_service_status(self):
        """
        Get the status of every Service in the registry.
        """
        return {
            service.__class__.__name__: await service.get_status()
            for service in self._service_registry
            if not service.__class__.__name__.startswith("_")
        }

    async def _cancel_service_tasks(self):
        self._service_task_set.cancel()

        try:
            await self._service_task_set
        except asyncio.CancelledError:
            pass
        except BaseException as e:
            await logger.aexception("ExceptionOccurred", error=str(e))

    def _register_core_services(self):
        # CoreService holds any RPC mechanisms available for
        # every server process like health and plugin management.
        from flowdapt.core.service import CoreService

        self.register_service(CoreService)

    def register_service(self, service: Type[Service], **kwargs):
        """
        Add an instance of Service to the registry
        """
        assert is_service(service), "Must be a subclass of Service"

        service_instance = service(self._context, **kwargs)
        self._service_registry.add(service_instance)

        logger.debug(
            "ServiceRegistered",
            type=type(service_instance).__name__,
            id=service_instance.__hash__(),
        )

    def _handle_signal(self, sig, *args):
        """
        Handle any kill signals. Will cancel all startup and main Service
        tasks. Won't cancel shutdown tasks as those must run.
        """
        log_once(log_method=logger.debug, event="SignalReceived", interval_seconds=1, signal=sig)

        if startup := self._task_sets.get("__startup__"):
            startup.cancel()

        if main := self._task_sets.get("__run__"):
            main.cancel()

        self._should_exit = True

    def _install_signal_handlers(self):
        """
        Installs all signals to listen for
        """
        for sig in (SIGINT, SIGTERM):
            self._loop.add_signal_handler(sig, self._handle_signal, sig)

    async def _create_and_await_task_set(
        self, service_method: str = "__run__", return_exceptions: bool = False
    ):
        """
        Create a new `TaskSet` and iterate over every Service, adding the
        method to the `TaskSet`. We then await it to gather results.
        `service_method` must be a valid method of the `Service` class.
        Catch any kill errors, and bubble up.
        """
        if not hasattr(Service, service_method):
            raise ValueError(f"{service_method} is not a valid Service method")

        task_results = None
        try:
            self._task_sets[service_method] = TaskSet(return_exceptions=return_exceptions)

            for service in self._service_registry:
                self._task_sets[service_method].add(getattr(service, service_method)())

            task_results = await self._task_sets[service_method]
        except (KeyboardInterrupt, asyncio.CancelledError):
            await logger.adebug("CancelEventReceived", service_method=service_method)  # noqa
        except Exception as e:
            await logger.aexception("ExceptionOccurred", error=str(e))
            task_results = e
        finally:
            # Cancel ourselves
            self._task_sets[service_method].cancel()

        if not return_exceptions and isinstance(task_results, Exception):
            raise task_results
        return task_results

    async def _do_run(self):
        """
        Run all run methods on each Service
        """
        self._context.flags["services_ready"] = True
        return await self._create_and_await_task_set("__run__")

    async def _do_startup(self):
        """
        Run all startup methods on each Service
        """
        return await self._create_and_await_task_set("__startup__")

    async def _do_shutdown(self):
        """
        Run all shutdown methods on each Service
        """
        self._context.flags["services_ready"] = False
        return await self._create_and_await_task_set("__shutdown__")

    async def run(self):
        """
        The main function to call. Performs the sequential startup, run, and
        shutdown functions of every registered Service. Installs all signal
        handlers and bubbles up any caught errors in the startup or run
        coroutines.
        """
        _logger = logger.bind(
            services=[service.__class__.__name__ for service in self._service_registry]
        )
        self._install_signal_handlers()

        await _logger.ainfo("ServicesStarting")
        async with self._context:
            try:
                await self._do_startup()
            except (asyncio.CancelledError, KeyboardInterrupt):
                await _logger.adebug("ServicesStartCancelled")
                self.should_exit = True
            except Exception as e:
                await _logger.aexception("ExceptionOccurred", error=str(e))

                self._should_exit = True

            if not self._should_exit:
                try:
                    await _logger.ainfo("ServicesReady")
                    await self._do_run()
                finally:
                    await _logger.ainfo("ServicesStopping")
                    await self._do_shutdown()
                    await self._cancel_service_tasks()


async def run_services(services: list[Type[Service]], context: dict[str, Any]):
    """
    Run a list of Services in the order they're provided. The context
    is passed to every Service.

    Example:

    ```py
    from flowdapt.lib.service import run_services
    from flowdapt.compute.service import ComputeService
    from flowdapt.triggers.service import TriggerService
    from flowdapt.lib.config import Configuration

    await run_services(
        services=[ComputeService, TriggerService],
        context={
            "config": Configuration(),
        }
    )
    ```
    """
    service_context = create_context(context)
    controller = ServiceController(service_context)

    for service in services:
        controller.register_service(service)

    await controller.run()
