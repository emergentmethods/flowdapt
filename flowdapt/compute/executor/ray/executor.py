import asyncio
import logging
from enum import Enum
from functools import partial
from typing import Any, AsyncIterator, Callable

import ray
from ray import ObjectRef
from ray import exceptions as ray_exc

from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.executor.ray.cluster_memory import RayClusterMemoryActor
from flowdapt.compute.executor.ray.utils import objectref_to_future
from flowdapt.compute.resources.workflow.context import WorkflowRunContext
from flowdapt.compute.resources.workflow.errors import WorkflowExecutionError
from flowdapt.compute.resources.workflow.graph import to_graph
from flowdapt.compute.resources.workflow.stage import BaseStage
from flowdapt.lib.config import get_app_dir, get_configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.plugins import get_user_modules_dir, list_plugins
from flowdapt.lib.utils.misc import dict_to_env_vars, import_from_string, normalize_env_vars
from flowdapt.lib.utils.model import model_dump


logger = get_logger(__name__)


class ExecuteStrategy(str, Enum):
    """
    The execution strategy to use for the RayExecutor.
    """

    # Submit each stage group to Ray as a separate task
    GROUP_BY_GROUP = "group_by_group"
    # Submit the entire graph to Ray as a single task
    ALL_AT_ONCE = "all_at_once"


class RayExecutor(Executor):
    """
    An Executor built on top of Ray. This is the recommended Executor
    since it's the most robust and scalable. Supports both local and distributed
    execution, and can be configured to use GPUs.

    To use this Executor, set the `services` > `compute` > `executor` config
    target, for example:

    ```yaml
    services:
      compute:
        executor:
          target: flowdapt.compute.executor.ray.RayExecutor
    ```

    :param cluster_address: The address of the Ray cluster to connect to. If not specified,
    will start a local cluster.
    :param cpus: The number of CPUs to use. If set to "auto", will use the number
    of CPUs on the machine. Ignored if connecting to external cluster.
    :param gpus: The number of GPUs to use. If set to "auto", will use the number
    of GPUs on the machine. Ignored if connecting to external cluster.
    :param resources: A dictionary of custom resource labels to use for the cluster. These labels
    are logical and not physical, and are used to determine if a stage can be run on a worker. Base
    resources such as CPUs and memory are automatically added. Defaults to an empty dictionary.
    Ignored if connecting to an external cluster.
    :param object_store_memory: The amount of memory to use for the Ray object store in bytes.
    Defaults to 1/3 of available memory. Ignored if connecting to an external cluster.
    :param dashboard_host: The host to bind the Ray dashboard to. Ignored if
    connecting to an external cluster.
    :param dashboard_port: The port to bind the Ray dashboard to. Ignored if
    connecting to an external cluster.
    :param log_to_driver: Whether to log to the driver or not.
    :param logging_level: The logging level to use.
    :param storage_dir: The directory to use for storing Ray data. Defaults to
    the app directory. Ignored if connecting to an external cluster.
    :param working_dir: The working directory to use in the runtime environment.
    :param py_modules: A list of Python modules to pass to the worker.
    :param pip: A list of pip packages to install on the worker.
    :param conda: A dictionary of conda packages to install on the worker.
    :param env_vars: A dictionary of environment variables to pass to the worker.
    :param container: A container image to use for the worker.
    :param cluster_memory_actor: A dictionary of options to use for the cluster memory actor.
    Requires a "name" key to be set. The rest of the options are passed to Ray. Defaults
    to a RayClusterMemoryActor with 1 CPU and a max concurrency of 1000.
    :param upload_plugins: Whether to upload plugins to the worker or not.
    :param runtime_env_config: A dictionary of options to use for the runtime environment config.
    For available options, see
    https://docs.ray.io/en/latest/ray-core/api/doc/ray.runtime_env.RuntimeEnvConfig.html.
    """

    kind: str = "ray"

    def __init__(
        self,
        cluster_address: str | None = None,
        strategy: str = ExecuteStrategy.GROUP_BY_GROUP,
        cpus: int | str = "auto",
        gpus: int | str | None = None,
        resources: dict[str, float] | None = None,
        object_store_memory: int | None = None,
        dashboard_host: str = "127.0.0.1",
        dashboard_port: int = 9969,
        log_to_driver: bool = True,
        logging_level: str | None = None,
        storage_dir: str | None = None,
        working_dir: str | None = None,
        py_modules: list[str] | None = None,
        pip: list[str] | None = None,
        conda: dict[str, str] | str | None = None,
        env_vars: dict[str, str] | None = None,
        container: dict[str, str] | None = None,
        upload_plugins: bool = True,
        cluster_memory_actor: dict[str, Any] | None = None,
        runtime_env_config: dict[str, Any] | None = None,
        **kwargs,
    ):
        _app_config = get_configuration()

        self._config: dict = {
            "cluster_address": cluster_address,
            "strategy": strategy,
            "cpus": cpus,
            "gpus": gpus,
            "resources": resources or {},
            "object_store_memory": int(float(object_store_memory)) if object_store_memory else None,
            "dashboard_host": dashboard_host,
            "dashboard_port": dashboard_port,
            "logging_level": logging_level or _app_config.logging.level,
            "log_to_driver": log_to_driver,
            "storage_dir": storage_dir,
            "working_dir": working_dir,
            "py_modules": py_modules,
            "pip": pip,
            "conda": conda,
            "env_vars": {
                **dict_to_env_vars(
                    model_dump(_app_config.logging, exclude_none=True), path="logging"
                ),
                **dict_to_env_vars(
                    model_dump(_app_config.storage, exclude_none=True), path="storage"
                ),
                **normalize_env_vars(env_vars or {}),
            },
            "container": container,
            "upload_plugins": upload_plugins,
            "cluster_memory_actor": cluster_memory_actor
            or {
                "name": "RayClusterMemoryActor",
                "num_cpus": 1,
                "max_concurrency": 1000,
            },
            "runtime_env_config": runtime_env_config,
            "kwargs": kwargs,
        }

        # Set the cluster memory actor name as env var to propagate
        # to the workflows
        assert self._config["cluster_memory_actor"]["name"], "Cluster memory actor name is required"
        self._config["env_vars"]["CM_ACTOR_NAME"] = self._config["cluster_memory_actor"]["name"]

        if not self._config["cluster_address"] or self._config["cluster_address"] == "local":
            # Set default storage dir to the app dir if not already specified
            app_dir = get_app_dir()
            if not self._config["storage_dir"] and app_dir:
                self._config["storage_dir"] = str(app_dir / "executor" / "ray" / "data")
            elif not self._config["storage_dir"] and not app_dir:
                self._config["storage_dir"] = "/tmp/data"

        self._ray_context = None
        self._is_local = (
            self._config["cluster_address"] is None or self._config["cluster_address"] == "local"
        )
        self._running_workflows: list[ObjectRef] = []

        if strategy == ExecuteStrategy.GROUP_BY_GROUP:
            self._call_attr = "remote"
        elif strategy == ExecuteStrategy.ALL_AT_ONCE:
            self._call_attr = "bind"
        else:
            raise ValueError(f"Invalid strategy: {strategy}")

    def _get_runtime_env(self) -> dict:
        py_modules = self._config["py_modules"] or []
        pip = self._config["pip"] or []

        if not self._is_local and self._config["upload_plugins"]:
            # Pass the module object itself and the list of
            # requirements as pip installs until https://github.com/ray-project/ray/issues/35559
            for plugin in list_plugins():
                # TODO: Add support for checking if user already specified a module and a version
                # Pass the plugin module to the worker
                py_modules.append(plugin.module)
                # Ensure requirements are installed
                pip.extend(plugin.metadata.requirements)

        if get_user_modules_dir():
            # Upload the user modules module to the worker
            # if it exists
            py_modules.append(import_from_string("user_modules", is_module=True))

        env = {
            "conda": self._config["conda"],
            "working_dir": self._config["working_dir"],
            "env_vars": self._config["env_vars"],
            "container": self._config["container"],
        }

        if py_modules:
            env["py_modules"] = py_modules
        if pip:
            env["uv"] = {"packages": pip}

        if self._config["runtime_env_config"]:
            env["config"] = self._config["runtime_env_config"]

        return env

    async def _init_ray(self):
        # We keep this method async so we can use async methods in the
        # subclassed Executors
        if self._config["log_to_driver"]:
            logging.basicConfig(level=logging.INFO)

        if self._is_local:
            if "mappers" not in self._config["resources"]:
                self._config["resources"]["mappers"] = 4

            context = ray.init(
                storage=self._config["storage_dir"],
                num_cpus=self._config["cpus"] if self._config["cpus"] != "auto" else None,
                num_gpus=self._config["gpus"] if self._config["gpus"] != "auto" else None,
                resources=self._config["resources"] if self._config["resources"] else None,
                object_store_memory=self._config["object_store_memory"],
                dashboard_host=self._config["dashboard_host"],
                dashboard_port=self._config["dashboard_port"],
                configure_logging=self._config["log_to_driver"],
                logging_level=self._config["logging_level"],
                log_to_driver=self._config["log_to_driver"],
                namespace="flowdapt",
                runtime_env=self._get_runtime_env(),
                ignore_reinit_error=True,
            )
        else:
            context = ray.init(
                address=self._config["cluster_address"],
                configure_logging=self._config["log_to_driver"],
                namespace="flowdapt",
                runtime_env=self._get_runtime_env(),
                ignore_reinit_error=True,
            )

        return context

    async def _close_ray(self):
        ray.shutdown()

    async def start(self):
        global logger
        logger = logger.bind(
            kind=self.kind,
            is_local=self._is_local,
            cluster_address=self._config["cluster_address"],
            strategy=self._config["strategy"],
        )

        await logger.ainfo("InitializingDriver")
        self._ray_context = await self._init_ray()

        await logger.ainfo("StartingClusterMemory")
        RayClusterMemoryActor.start(
            self._config["cluster_memory_actor"].pop("name"), **self._config["cluster_memory_actor"]
        )
        await logger.ainfo("StartedClusterMemory")

        dashboard_url = self._ray_context.dashboard_url or None
        self.running = True

        await logger.ainfo("DriverInitialized", dashboard=dashboard_url)

    async def reload_environment(self):
        await self.close()
        await self.start()

    async def close(self):
        if self.running:
            if ray.is_initialized():
                # Cancel any running workflows we submitted if we're shutting down
                for object_ref in self._running_workflows:
                    await logger.ainfo("WorkflowCancelling", objectref=object_ref)
                    ray.cancel(object_ref)

                self._running_workflows = []
                await self._close_ray()

            self._ray_context = None
            self.running = False

    async def environment_info(self):
        return {
            "dashboard_url": self._ray_context.dashboard_url,
            # We can't use gcs address until the following issue is
            # resolved:
            # https://github.com/ray-project/ray/issues/36833
            # "gcs_address": runtime_context.gcs_address,
            "nodes": ray.nodes(),
        }

    def _check_resources(self, stage: BaseStage):
        """
        Ensure the executor has enough resources to run a stage.
        """
        stage_resources = stage.get_required_resources()

        required_resources = {
            "CPU": stage_resources.pop("cpus", 0.0),
            "GPU": stage_resources.pop("gpus", 0.0),
            "memory": stage_resources.pop("memory", 0.0),
            **stage_resources,
        }
        available_resources = [node["Resources"] for node in ray.nodes()]

        for resource_dict in available_resources:
            for key in required_resources:
                value = required_resources[key]
                if value is not None:
                    if resource_dict.get(key, 0) < value:
                        available = resource_dict.get(key, 0)
                        resource = key
                        break
            else:
                return True

        raise WorkflowExecutionError(
            f"Insufficient resources to run stage `{stage.name}`. "
            f"Required {value} {resource} but only {available} available."
        )

    def _create_lazy(self, func: Callable, **options):
        return ray.remote(func).options(**options)

    def lazy(self, stage: BaseStage):
        part = partial(
            lambda func, **options: getattr(self._create_lazy(func, **options), self._call_attr),
            name=stage.name,
            resources=stage.resources.extras(),
            num_cpus=stage.resources.cpus,
            num_gpus=stage.resources.gpus,
            memory=stage.resources.memory,
        )
        return part(stage.get_stage_fn())

    def mapped_lazy(self, stage: BaseStage) -> Any:
        def map_inner(iterable, *args, **kwargs):
            """
            Map a function to an iterable using ray.remote
            """
            # Make sure we're keeping the same resource requirements
            # for the inner function
            func = stage.get_stage_fn()
            options = {
                "name": stage.name,
                "resources": stage.resources.extras(),
                "num_cpus": stage.resources.cpus,
                "num_gpus": stage.resources.gpus,
                "memory": stage.resources.memory,
            }
            wrapped = ray.remote(func).options(**options)

            return ray.get([wrapped.remote(item, *args, **kwargs) for item in iterable])

        return getattr(self._create_lazy(map_inner, resources={"mappers": 1}), self._call_attr)

    async def _generate_partials(
        self,
        definition: WorkflowResource,
        context: WorkflowRunContext,
        include_output: bool = False,
    ) -> AsyncIterator[Any]:
        workflow_graph = to_graph(definition)
        ray_graph: dict = {}

        for stage_group in workflow_graph:
            group_partials: dict = {}

            for stage_name in stage_group:
                stage = workflow_graph.get_stage(stage_name)

                # Check if the Executor has the required resources for this Stage
                self._check_resources(stage)

                args: list = []
                kwargs: dict = {}

                if stage.depends_on:
                    # If the stage depends on a previous stage, the return values
                    # of those previous stages are positional arguments in this one
                    args.extend([ray_graph[dep] for dep in stage.depends_on])
                else:
                    # We assume the stage with no dependencies is the first stage
                    # so we pass the payload as the kwargs to begin with
                    kwargs.update(context.input)

                stage_partial = stage.get_partial(
                    executor=self, context=context, args=args, kwargs=kwargs
                )

                ray_graph[stage_name] = group_partials[stage_name] = stage_partial

            yield group_partials

    async def _execute_group_by_group(
        self, definition: WorkflowResource, context: WorkflowRunContext
    ):
        results: dict = {}

        async for stage_group in self._generate_partials(definition, context):
            stage_names = list(stage_group.keys())
            group_partials = [objectref_to_future(part) for part in stage_group.values()]

            # Wait for all stages in the group to finish, and catch any errors
            # before moving on. This ensures we don't submit any stages that
            # depend on a stage that errored out, and that Ray doesn't have a come apart
            # because it's trying to submit the error as the input to the next function.
            # It's slightly slower than submitting all stages at once, but it's
            # more robust. Meant for testing and debugging.
            try:
                group_results = dict(
                    zip(stage_names, await asyncio.gather(*group_partials), strict=False)
                )
            except (ray_exc.TaskCancelledError, asyncio.CancelledError, ray_exc.RayTaskError) as e:
                raise WorkflowExecutionError("Workflow cancelled") from e
            except ConnectionError as e:
                raise WorkflowExecutionError("Lost connection to Executor") from e
            except BaseException as e:
                raise WorkflowExecutionError(f"Unknown error occurred: {str(e)}") from e

            results.update(group_results)

        # We return the output from the final stage if there is only one,
        # otherwise we return a list of all outputs from each stage in
        # the last group
        if len(stage_names) > 1:
            result = [results[stage_name] for stage_name in stage_names]
        else:
            result = results[stage_names[0]]
        return result

    async def _execute_all_at_once(self, definition: WorkflowResource, context: WorkflowRunContext):
        async for stage_group in self._generate_partials(definition, context):
            final_group = stage_group

        object_refs = [
            (stage_name, output_node.execute()) for stage_name, output_node in final_group.items()
        ]
        futures = [
            (stage_name, objectref_to_future(object_ref)) for stage_name, object_ref in object_refs
        ]

        self._running_workflows.extend(object_refs)
        try:
            result = await asyncio.gather(*[fut for _, fut in futures])

            if len(object_refs) == 1:
                return result[0]
            else:
                return result

        except (ray_exc.TaskCancelledError, asyncio.CancelledError, ConnectionError) as e:
            raise WorkflowExecutionError("Workflow cancelled") from e
        except ray_exc.RayTaskError as e:
            raise WorkflowExecutionError(str(e)) from e
        except BaseException as e:
            raise WorkflowExecutionError(f"Unknown error occurred: {str(e)}") from e
        finally:
            for object_ref in object_refs:
                if object_ref in self._running_workflows:
                    self._running_workflows.remove(object_ref)

    async def __call__(
        self, definition: WorkflowResource, run: WorkflowRun, context: WorkflowRunContext
    ):
        """
        Execute a Workflow given a definition, run and a payload.

        :param definition: Workflow definition
        :type definition: WorkflowDefinition
        :param run: Workflow run
        :type run: WorkflowRun
        :param context: Workflow run context
        :type context: WorkflowRunContext
        :return: Workflow result
        """
        match self._config["strategy"]:
            case ExecuteStrategy.GROUP_BY_GROUP:
                return await self._execute_group_by_group(definition, context)
            case ExecuteStrategy.ALL_AT_ONCE:
                return await self._execute_all_at_once(definition, context)
            case _:
                raise ValueError(f"Invalid strategy: {self._config['strategy']}")
