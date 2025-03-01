import asyncio
import sys
from concurrent.futures import Executor as PoolExecutor
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Iterable

from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.executor.local.cluster_memory import SOCKET_PATH, ClusterMemoryServer
from flowdapt.compute.resources.workflow.context import WorkflowRunContext
from flowdapt.compute.resources.workflow.graph import to_graph
from flowdapt.compute.resources.workflow.stage import BaseStage
from flowdapt.compute.utils import (
    get_available_cores,
)
from flowdapt.lib.serializers import CloudPickleSerializer
from flowdapt.lib.utils.asynctools import is_async_callable, run_in_thread


def lazy_func(func: Callable, pool: PoolExecutor):
    async def _wrapper(*args, **kwargs):
        if is_async_callable(func):
            return await func(*args, **kwargs)
        else:
            return await asyncio.get_running_loop().run_in_executor(
                pool, partial(func, *args, **kwargs)
            )

    return _wrapper


def run_func_from_cloudpickle(fn, /, *args, **kwargs):
    return CloudPickleSerializer.loads(fn)(*args, **kwargs)


# Subclass ProcessPoolExecutor to use cloudpickle to serialize
# functions before sending them to the worker processes since it's
# more robust than the default pickle implementation.
class CloudPickleProcessPoolExecutor(ProcessPoolExecutor):
    def submit(self, fn, /, *args, **kwargs):
        return super().submit(
            run_func_from_cloudpickle, CloudPickleSerializer.dumps(fn), *args, **kwargs
        )


class LocalExecutor(Executor):
    """
    A Local based Executor for running workflows eagerly in a testing
    environment. Built on top of `concurrent.Futures`.

    This Executor is best used for testing and debugging workflows locally.
    It does not support distributed execution, and is not recommended for
    production use. It also does nothing to manage resources on the machine,
    and ignores any set stage resources.

    To use this Executor, set the `services` > `compute` > `executor` config
    target, for example:

    ```yaml
    services:
      compute:
        executor:
          target: flowdapt.compute.executor.local.LocalExecutor
    ```

    :param use_processes: Whether to use a ProcessPoolExecutor or a ThreadPoolExecutor
    :param cpus: The number of processes/threads to use. If set to "auto", will use the number
    of CPUs on the machine.
    :param cluster_memory_socket_path: The path to the socket file for the ClusterMemoryServer,
    defaults to `/tmp/flowdapt-cluster-memory.sock`
    """

    kind: str = "local"

    def __init__(
        self,
        use_processes: bool = True,
        cpus: int | str = "auto",
        cluster_memory_socket_path: str = SOCKET_PATH,
    ) -> None:
        self._closed = asyncio.Event()
        self._loop = asyncio.get_running_loop()

        actual_cpus = get_available_cores() if cpus == "auto" else cpus

        self._config = {
            "use_processes": use_processes,
            "cpus": actual_cpus,
            "cluster_memory_socket_path": cluster_memory_socket_path,
        }

        self._pool: PoolExecutor

    async def start(self) -> None:
        if self.running:
            return

        if self._config["use_processes"]:
            self._pool = CloudPickleProcessPoolExecutor(self._config["cpus"])
        else:
            self._pool = ThreadPoolExecutor(self._config["cpus"])

        self._cm_path = self._config["cluster_memory_socket_path"]
        self._cm_server: ClusterMemoryServer = ClusterMemoryServer(self._cm_path)

        await self._cm_server.start()
        self.running = True

    async def close(self):
        if not self.running:
            return

        if self._pool:
            self._pool.shutdown(wait=True)

        await self._cm_server.close()
        self.running = False

    async def reload_environment(self):
        await self.close()
        await self.start()

    async def environment_info(self):
        return {
            "processes": self._config["use_processes"],
            "cpus": self._config["cpus"],
            "cluster_memory": {
                "path": self._cm_path,
                "serializer": self._cm_server._serializer.__name__,
                "store_size": sys.getsizeof(self._cm_server._store),
            },
        }

    # For support when entered directly in context
    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def __call__(
        self, definition: WorkflowResource, run: WorkflowRun, context: WorkflowRunContext
    ) -> Any:
        if not self.running:
            raise RuntimeError("LocalExecutor was not started")

        graph = to_graph(definition)
        results: dict = {}

        for group in graph:
            coroutines = []

            for stage_name in group:
                stage = graph.get_stage(stage_name)

                if stage.depends_on:
                    args = [results[dep] for dep in stage.depends_on]
                    kwargs = {}
                else:
                    args = []
                    kwargs = context.input

                stage_partial = stage.get_partial(
                    executor=self, context=context, args=args, kwargs=kwargs
                )

                coroutines.append(stage_partial)

            outputs = await asyncio.gather(*coroutines)
            results.update(dict(zip(group, outputs, strict=False)))

        return results[stage_name]

    def lazy(self, stage: BaseStage):
        return lazy_func(stage.get_stage_fn(), pool=self._pool)

    def mapped_lazy(self, stage: BaseStage) -> Any:
        part = partial(lazy_func, pool=self._pool)

        def map_inner(iterable: Iterable, *args, **kwargs):
            if not stage.is_async:
                func = stage.get_stage_fn()
            else:
                func = partial(run_in_thread, stage.get_stage_fn())

            return [func(item, *args, **kwargs) for item in iterable]

        return part(map_inner)
