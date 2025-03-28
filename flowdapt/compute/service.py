import asyncio

from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.compute.rpc import register_rpc
from flowdapt.lib.config import Configuration
from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc import RPC
from flowdapt.lib.service import Service
from flowdapt.lib.utils.asynctools import cancel_task
from flowdapt.lib.utils.misc import get_full_path_type


logger = get_logger(__name__, service="compute")


class ComputeService(Service):
    """
    Compute Service is responsible for managing WorkflowResources, executing
    them, as well as WorkflowRuns.
    """

    def __initialize__(self, **kwargs) -> None:
        self._config: Configuration = self._context.config
        # Typing fix
        assert not isinstance(self._config.services.compute, str)

        self._rpc: RPC = self._context.rpc
        self._db: BaseStorage = self._context.database

        # Create the Executor object and attach to the context
        self._executor = self._config.services.compute.executor.instantiate()
        self._context["executor"] = self._executor

        # Register the API spec with the version specified
        register_rpc(self._rpc)

        self._expire_task = None
        self._stopped = asyncio.Event()

    async def get_status(self):
        return {
            "status": "OK",
            "executor": get_full_path_type(self._executor),
            "environment": await self._executor.environment_info(),
        }

    async def _expire_workflow_runs(self):
        retention_duration = self._config.services.compute.run_retention_duration

        while not self._stopped.is_set():
            try:
                if retention_duration <= 0:
                    return

                if runs := await WorkflowRun.get_by_age(self._db, retention_duration):
                    await logger.ainfo(
                        "ExpiringWorkflowRuns",
                        num_runs=len(runs),
                        retention_duration=retention_duration,
                    )
                    await self._db.delete(runs)
            except asyncio.CancelledError:
                return
            except Exception as e:
                await logger.aerror("ExceptionOccurred", error=str(e))
            finally:
                await asyncio.sleep(15)

    async def __startup__(self):
        global logger
        logger = logger.bind(
            executor=self._executor.__class__.__name__,
        )

        await logger.ainfo("ServiceStarting")

        self._stopped.clear()
        await self._executor.start()

        if not self._expire_task:
            self._expire_task = asyncio.create_task(self._expire_workflow_runs())

        await logger.ainfo("ServiceStarted")

    async def __shutdown__(self):
        await logger.ainfo("ServiceStopping")

        self._stopped.set()
        await self._executor.close()

        if self._expire_task:
            await cancel_task(self._expire_task)

        await logger.ainfo("ServiceStopped")

    async def __run__(self):
        await self._rpc.wait_until_finished()
