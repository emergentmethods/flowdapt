import logging
import warnings
from copy import copy
from functools import partial
from typing import Any, Callable, Iterable, Literal

from dask import delayed
from dask.base import tokenize
from distributed import Client, SpecCluster, worker_client
from distributed.nanny import Nanny
from distributed.scheduler import Scheduler
from distributed.versions import VersionMismatchWarning

from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.executor.dask.gpu_cluster import GPUCluster
from flowdapt.compute.executor.dask.plugins import (
    Environ,
    PipInstall,
    SetupPluginRequirements,
    UploadDirectory,
    UploadPlugins,
)
from flowdapt.compute.resources.workflow.context import WorkflowRunContext
from flowdapt.compute.resources.workflow.graph import WorkflowGraph, to_graph
from flowdapt.compute.resources.workflow.stage import BaseStage
from flowdapt.compute.utils import (
    get_available_cores,
    get_total_memory,
)
from flowdapt.lib.config import get_configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.plugins import (
    get_user_modules_dir,
    has_plugins,
    list_plugins,
)
from flowdapt.lib.utils.misc import dict_to_env_vars, normalize_env_vars, parse_bytes
from flowdapt.lib.utils.model import model_dump


# Ignore Dask version mismatch warnings
# A warning means a version patch is different between the Client
# and the Cluster. This is fine, if it's more than a patch then it will
# raise an error.
warnings.filterwarnings("ignore", category=VersionMismatchWarning)
logger = get_logger(__name__)


# Keep the inners in module scope so they can be pickled
# because Dask's pickling is funny and can't do method locals
def lazy_inner(func: Callable, name: str, *args, **kwargs):
    """
    Wrap a function in dask.delayed
    """
    return delayed(func, name=name)(*args, **kwargs)


def map_inner(func: Callable, name: str, resources: dict, iterable: Iterable, *args, **kwargs):
    """
    Map a function to an iterable using dask.delayed
    """
    with worker_client() as client:
        futs = [
            delayed(func)(
                item,
                *args,
                **{
                    **kwargs,
                    "dask_key_name": f"{name}-{tokenize(item)}",
                },
            )
            for item in iterable
        ]

        return client.compute(futs, resources=resources, sync=True)


class DaskExecutor(Executor):
    """
    An Executor built on top of Dask. Supports both local and distributed
    execution, and can be configured to use GPUs. Often best for larger than
    memory workloads.

    To use this Executor, set the `services` > `compute` > `executor` config
    target, for example:

    ```yaml
    services:
      compute:
        executor:
          target: flowdapt.compute.executor.dask.DaskExecutor
    ```

    :param cluster_address: The address of an existing Dask cluster to connect to.
    :param scheduler_host: The host to start the scheduler on.
    :param scheduler_port: The port to start the scheduler on.
    :param scheduler_scheme: The protocol to use for the scheduler.
    :param dashboard_port: The port to start the dashboard on.
    :param cpus: The number of CPUs to use. If set to "auto", will use the number
    of CPUs on the machine.
    :param gpus: The number of GPUs to use, or a comma delimited list of device ID's. If
    set to "auto", will use the number of GPUs on the machine. Defaults to "disabled".
    :param threads: The number of threads to use. Defaults to all available.
    :param memory: The amount of memory to use. Defaults to all available.
    :param adaptive: Whether to use adaptive scaling. Defaults to False.
    :param resources: A dictionary of custom resource labels to use for the cluster. These labels
    are logical and not physical, and are used to determine if a stage can be run on a worker. Base
    resources such as CPUs and memory are automatically added. Defaults to an empty dictionary.
    :param pip: A list of pip packages to install on the workers. Defaults to an empty list.
    :param env_vars: A dictionary of environment variables to set on the workers. Defaults to an
    empty dictionary.
    :param upload_plugins: Whether to upload plugins to the workers. This is ignored if running an
    in-process cluster. Defaults to False.
    """

    kind: str = "dask"
    client: Client

    def __init__(
        self,
        cluster_address: str | None = None,
        scheduler_host: str = "127.0.0.1",
        scheduler_port: int = 6684,
        scheduler_scheme: str = "tcp",
        dashboard_port: int = 9968,
        cpus: int | Literal["auto"] = "auto",
        gpus: int | str = "disabled",
        threads: int | Literal["auto"] = "auto",
        memory: str = "auto",
        adaptive: bool = False,
        pip: list[str] = [],
        env_vars: dict[str, str] = {},
        resources: dict[str, float] = {},
        upload_plugins: bool = False,
    ):
        _app_config = get_configuration()

        match cpus:
            case "auto":
                actual_cpus = get_available_cores()
            case _:
                actual_cpus = min(cpus, get_available_cores())

        match threads:
            case "auto":
                actual_threads = get_available_cores()
            case _:
                actual_threads = threads

        match memory:
            case "auto":
                actual_memory = int(get_total_memory() / actual_cpus)
            case _:
                actual_memory = parse_bytes(memory)

        self._config: dict[str, Any] = {
            "cluster_address": cluster_address,
            "scheduler_host": scheduler_host,
            "scheduler_port": scheduler_port,
            "scheduler_scheme": scheduler_scheme,
            "dashboard_port": dashboard_port,
            "cpus": actual_cpus,
            "gpus": gpus,
            "threads": actual_threads,
            "memory": actual_memory,
            "pip": pip,
            "env_vars": {
                **dict_to_env_vars(
                    model_dump(_app_config.logging, exclude_none=True), path="logging"
                ),
                **dict_to_env_vars(
                    model_dump(_app_config.storage, exclude_none=True), path="storage"
                ),
                **normalize_env_vars(env_vars or {}),
            },
            "adaptive": adaptive,
            "resource_labels": {str(k): parse_bytes(v) for k, v in resources.items()},
            "upload_plugins": upload_plugins,
        }

        # Update resource labels with actual resources
        self._config["resource_labels"].update(
            {"cpus": actual_cpus, "memory": actual_memory, "threads": actual_threads}
        )

        self._cluster: SpecCluster | str
        self.client: Client
        self._registered_plugins: list[str] = []

    @property
    def is_external(self) -> bool:
        return isinstance(self._cluster, str)

    async def _get_cluster(self) -> SpecCluster:
        scheduler_spec = {
            "cls": Scheduler,
            "options": {
                "dashboard": True,
                "dashboard_address": f":{self._config['dashboard_port']}",
                "host": self._config["scheduler_host"],
                "port": self._config["scheduler_port"],
                "protocol": self._config["scheduler_scheme"],
            },
        }
        worker_spec = {
            "cls": Nanny,
            "options": {
                "silence_logs": logging.CRITICAL,
                "quiet": True,
                "nthreads": self._config["threads"],
                "resources": self._config["resource_labels"],
                "memory_limit": self._config["memory"],
            },
        }

        return await GPUCluster(
            gpus=self._config["gpus"],
            scheduler=scheduler_spec,
            worker=worker_spec,
        )

    async def _register_dask_plugins(self) -> None:
        pip_packages = copy(self._config["pip"])

        # Register environment variables first
        if env_vars := copy(self._config["env_vars"]):
            await logger.ainfo("RegisteringDaskPlugin", plugin="EnvironmentVariables")
            await self.client.register_worker_plugin(Environ(env_vars), name="env_vars", nanny=True)

        if pip_packages:
            await logger.ainfo("RegisteringDaskPlugin", plugin="PipInstall")
            await self.client.register_worker_plugin(
                PipInstall(pip_packages, restart=True),
                name="pip_install",
            )

        user_modules_dir = get_user_modules_dir()

        # Upload the user modules
        if user_modules_dir:
            await logger.ainfo("RegisteringDaskPlugin", plugin="UploadUserModules")
            await self.client.register_worker_plugin(
                UploadDirectory(
                    str(user_modules_dir),
                    skip=(lambda filename: filename.endswith(".py") is False,),
                    restart=False,
                    update_path=True,
                ),
                name="upload_user_modules",
                nanny=True,
            )

        # If we don't have an plugin dir then we don't have any plugins to add
        if has_plugins() and self.is_external and self._config["upload_plugins"]:
            plugins_list = list_plugins()

            await logger.ainfo("RegisteringDaskPlugin", plugin="SetupPluginRequirements")
            await self.client.register_worker_plugin(
                SetupPluginRequirements(plugins=plugins_list),
                name="setup_plugin_requirements",
                nanny=True,
            )

            await logger.ainfo("RegisteringDaskPlugin", plugin="UploadPlugins")
            await self.client.register_worker_plugin(
                UploadPlugins(plugins=plugins_list), name="upload_plugins", nanny=True
            )

    async def start(self) -> None:
        global logger
        logger = logger.bind(kind=self.kind)

        if self._config["cluster_address"]:
            await logger.ainfo(
                "UsingExternalCluster", cluster_address=self._config["cluster_address"]
            )
            self._cluster = self._config["cluster_address"]
        else:
            await logger.ainfo("UsingLocalCluster")
            self._cluster = await self._get_cluster()

            # If we're set to auto then start the adaptive
            if self._config["adaptive"]:
                await logger.ainfo(
                    "InitializingAdaptiveScaling", minimum=1, maximum=self._config["cpus"]
                )
                self._cluster.adapt(minimum=1, maximum=self._config["cpus"], interval="1s")
            # Otherwise just scale to that amount right away
            else:
                await logger.ainfo("InitializingStaticScaling", number=self._config["cpus"])
                self._cluster.scale(self._config["cpus"])

        # Create the client for the cluster
        await logger.ainfo(
            "InitializingDriver",
            cluster=self._cluster
            if isinstance(self._cluster, str)
            else self._cluster.__class__.__name__,
        )
        self.client = await Client(self._cluster, asynchronous=True)

        if self.is_external:
            await self.client.forward_logging()

        # TODO: Services will likely require some type of leader election
        # when running in distributed mode. We need to make use of that here
        # when setting up the environment while using multiple replicas of the
        # compute service. Only the leader should be managing environment.
        # Install the Dask plugins needed to manage the environment
        await self._register_dask_plugins()

        dashboard_url = self.client.dashboard_link
        self.running = True

        await logger.ainfo("DriverInitialized", dashboard=dashboard_url)

    async def close(self) -> None:
        try:
            await self.client.close()
        except BaseException as e:
            await logger.aexception("FailedToCloseDriver", error=e)

        if self._cluster and isinstance(self._cluster, SpecCluster):
            await self._cluster.close()

        self.running = False

    async def reload_environment(self):
        # TODO: Actually implement this
        await self.close()
        await self.start()

    async def environment_info(self):
        return {
            **self.client.scheduler_info(),
            "dashboard_link": self.client.dashboard_link,
        }

    def _check_resources(self, stage: BaseStage) -> None:
        """
        Check if the Cluster has enough resources to run the stage
        """
        stage_resources = stage.get_required_resources()
        workers = self.client.scheduler_info()["workers"].values()

        for resource, required_amount in stage_resources.items():
            available_amount = sum(worker["resources"].get(resource, 0) for worker in workers)
            if required_amount is not None:
                if available_amount < required_amount:
                    raise RuntimeError(
                        f"Insufficient resources to run stage {stage.name}. "
                        f"Required {required_amount} {resource} but only "
                        f"{available_amount} available."
                    )

    async def __call__(
        self, definition: WorkflowResource, run: WorkflowRun, context: WorkflowRunContext
    ):
        if not self.client:
            raise RuntimeError("DaskExecutor has not been started.")

        # TODO: Pass stage resources to client.compute
        dask_graph = self._build_dask_graph(to_graph(definition), context)
        return await self._compute_dask_graph(dask_graph)

    async def _compute_dask_graph(self, dask_graph: dict[str, Any]) -> tuple[Any]:
        # Compute the graph given the last stage and return it's output
        return await self.client.compute(list(dask_graph.values())[-1])

    def _build_dask_graph(
        self, workflow_graph: WorkflowGraph, context: WorkflowRunContext
    ) -> dict[str, Any]:
        dask_graph: dict[str, Callable[..., Any]] = {}

        for stage_group in workflow_graph:
            for stage_name in stage_group:
                stage = workflow_graph.get_stage(stage_name)

                self._check_resources(stage)

                args: list = []
                kwargs: dict = {}

                if stage.depends_on:
                    args = [dask_graph[dep] for dep in stage.depends_on]
                else:
                    kwargs.update(context.input)

                dask_graph[stage_name] = stage.get_partial(
                    executor=self, context=context, args=args, kwargs=kwargs
                )

        return dask_graph

    def lazy(self, stage: BaseStage):
        return partial(
            delayed(stage.get_stage_fn()),
            dask_key_name=stage.name,
        )

    def mapped_lazy(self, stage: BaseStage):
        return delayed(
            partial(map_inner, stage.get_stage_fn(), stage.name, stage.get_required_resources())
        )
