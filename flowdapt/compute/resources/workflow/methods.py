import asyncio
from time import process_time_ns
from typing import Any, Type
from uuid import UUID

from flowdapt.compute.domain.events.workflow import (
    Event,
    WorkflowFinishedEvent,
    WorkflowStartedEvent,
)
from flowdapt.compute.domain.models.config import ConfigResource
from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun, WorkflowRunState
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.resources.config.methods import get_merged_config_data
from flowdapt.compute.resources.workflow.execute import execute_workflow
from flowdapt.lib.config import Configuration
from flowdapt.lib.context import inject_context
from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.errors import ResourceNotFoundError
from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc import RPC
from flowdapt.lib.telemetry import Status, StatusCode, get_meter, get_tracer
from flowdapt.lib.utils.model import model_dump
from flowdapt.lib.utils.taskset import TaskSet


logger = get_logger(__name__)
tracer = get_tracer(__name__)
meter = get_meter(__name__)

workflows_executed_count = meter.create_counter(
    name="workflows_executed", description="Number of workflows ran", unit="1"
)
workflow_execution_time = meter.create_histogram(
    name="workflow_execution_time", description="Time to execute a workflow", unit="ms"
)
workflows_failed_count = meter.create_counter(
    name="workflows_failed", description="Number of failed workflows", unit="1"
)


async def _publish_workflow_run_event(rpc: RPC, event_type: Type[Event], run: WorkflowRun):
    await logger.adebug("PublishingEvent", event_type=event_type.__name__)
    await rpc.event_bus.publish(event_type(source="compute", data=run))


async def _get_workflow(identifier: str | UUID, database: BaseStorage) -> WorkflowResource:
    workflow = await WorkflowResource.get(database, identifier)
    if not workflow:
        raise ResourceNotFoundError
    return workflow


async def _get_workflow_run(identifier: str | UUID, database: BaseStorage) -> WorkflowRun | None:
    return await WorkflowRun.get(database, identifier)


@tracer.start_as_current_span("list_workflows")
@inject_context
async def list_workflows(database: BaseStorage) -> list[WorkflowResource]:
    """
    List all WorkflowResources.

    :param database: The database to use
    :return: A list of WorkflowResources
    """
    async with database.transaction():
        return await WorkflowResource.get_all(database)


@tracer.start_as_current_span("create_workflow")
@inject_context
async def create_workflow(payload: WorkflowResource, database: BaseStorage) -> WorkflowResource:
    """
    Create a WorkflowResource given a payload.

    :param payload: The WorkflowResource to create
    :param database: The database to use
    :return: The created WorkflowResource
    """
    async with database.transaction():
        await payload.insert(database)
        return payload


@tracer.start_as_current_span("update_workflow")
@inject_context
async def update_workflow(
    identifier: str | UUID, payload: WorkflowResource, database: BaseStorage
) -> WorkflowResource:
    """
    Update a WorkflowResource given a payload.

    :param identifier: The identifier of the WorkflowResource to update
    :param payload: The WorkflowResource to update
    :param database: The database to use
    :return: The updated WorkflowResource
    """
    async with database.transaction():
        workflow = await _get_workflow(identifier, database)
        await workflow.update(database, model_dump(payload))
        return workflow


@tracer.start_as_current_span("get_workflow")
@inject_context
async def get_workflow(identifier: str | UUID, database: BaseStorage) -> WorkflowResource:
    """
    Get a WorkflowResource given an identifier.

    :param identifier: The identifier of the WorkflowResource to get
    :param database: The database to use
    :return: The WorkflowResource
    """
    async with database.transaction():
        return await _get_workflow(identifier, database)


@tracer.start_as_current_span("delete_workflow")
@inject_context
async def delete_workflow(identifier: str | UUID, database: BaseStorage) -> WorkflowResource:
    """
    Delete a WorkflowResource given an identifier.

    :param identifier: The identifier of the WorkflowResource to delete
    :param database: The database to use
    :return: The deleted WorkflowResource
    """
    async with database.transaction():
        workflow = await _get_workflow(identifier, database)
        await workflow.delete(database)
        return workflow


@inject_context
async def run_workflow(
    identifier: str,
    input: dict,
    database: BaseStorage,
    task_set: TaskSet,
    rpc: RPC,
    config: Configuration,
    executor: Executor,
    wait: bool = True,
    namespace: str | None = None,
    source: str | None = None,
) -> Any:
    """
    Run a Workflow optionally given an input

    :param identifier: The identifier of the Workflow to run
    :param input: The input to pass to the Workflow
    :param database: The database to use
    :param task_set: The TaskSet to add the task to
    :param rpc: The RPC client to use
    :param config: The Application Configuration
    :param executor: The Executor to use
    :param wait: Whether to wait for the task to finish or not
    :param namespace: The namespace to run the Workflow in
    :param source: The source that triggered this workflow to run
    """
    # We don't use the tracer decorator here because we want the span
    # to end when the task is done
    with tracer.start_as_current_span("run_workflow", end_on_exit=False) as span:
        definition = await _get_workflow(identifier, database)

        run_info = {"workflow": definition.metadata.name, "source": source or "manual"}
        if config.services.compute.run_retention_duration != 0:
            workflow_run = await WorkflowRun.create(database, run_info)
        else:
            workflow_run = WorkflowRun(**run_info)

        run_task = task_set.add(
            _run_workflow(
                definition=definition,
                input=input,
                namespace=namespace,
                span=span,
                run=workflow_run,
                database=database,
                rpc=rpc,
                config=config,
                executor=executor,
            )
        )
        run_task.add_done_callback(lambda _: span.end())

        if wait:
            await asyncio.wait([run_task])

        return workflow_run


async def _run_workflow(
    definition: WorkflowResource,
    input: dict,
    namespace: str | None,
    span: Any,
    run: WorkflowRun,
    database: BaseStorage,
    rpc: RPC,
    config: Configuration,
    executor: Executor,
) -> Any:
    namespace = namespace or config.services.compute.default_namespace

    # Set the span attributes
    span.set_attribute("workflow.uid", str(definition.metadata.uid))
    span.set_attribute("workflow.name", definition.metadata.name)
    span.set_attribute("workflow.executor", executor.kind)
    span.set_attribute("workflow.namespace", str(namespace))
    span.set_attribute("workflow.run.uid", str(run.uid))
    span.set_attribute("workflow.run.started_at", str(run.started_at))

    metrics_attributes = {
        "workflow.uid": str(definition.metadata.uid),
        "workflow.name": definition.metadata.name,
        "workflow.executor": executor.kind,
        "workflow.namespace": str(namespace),
        "workflow.run.uid": str(run.uid),
        "workflow.run.started_at": str(run.started_at),
        "workflow.run.source": str(run.source),
    }

    _logger = logger.bind(
        uid=definition.metadata.uid,
        name=definition.metadata.name,
        executor=executor.kind,
        namespace=namespace,
        run_uid=run.uid,
        source=run.source,
    )

    try:
        # Get any associated Configs
        configs = await ConfigResource.get_configs(database, definition)
        config_data = get_merged_config_data(configs)

        workflows_executed_count.add(1, metrics_attributes)

        # Set the WorkflowRun to running and fire the start event
        run.set_state(WorkflowRunState.running)

        if config.services.compute.run_retention_duration != 0:
            await run.update(database)

        await _logger.ainfo("WorkflowRunStarted")
        await _publish_workflow_run_event(rpc, WorkflowStartedEvent, run)

        with tracer.start_as_current_span("run_workflow__execute_workflow"):
            _ = process_time_ns()

            # Execute the workflow
            await execute_workflow(
                definition,
                input=input,
                namespace=namespace,
                run=run,
                executor=executor,
                config=config_data,
                return_result=True,
            )

            workflow_execution_time.record((process_time_ns() - _) / 1e6, metrics_attributes)

    except Exception as e:
        await _logger.aexception("WorkflowRunFailed", error=str(e))

        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR))

        workflows_failed_count.add(1, metrics_attributes)
    finally:
        # Save the WorkflowRun and fire the finished event
        if config.services.compute.run_retention_duration != 0:
            await run.update(database)

        await _publish_workflow_run_event(rpc, WorkflowFinishedEvent, run)

        span.set_attribute("workflow.run.finished_at", str(run.finished_at))
        span.set_attribute("workflow.run.state", run.state)

        await _logger.ainfo("WorkflowRunFinished")

        return run


@tracer.start_as_current_span("get_recent_workflow_runs")
@inject_context
async def get_recent_workflow_runs(
    workflow: str, database: BaseStorage, limit: int = 10
) -> list[WorkflowRun]:
    """
    Get a list of recent WorkflowRuns for a given WorkflowResource.

    :param workflow: The WorkflowResource to get the WorkflowRuns for
    :param database: The database to use
    :param limit: The limit of WorkflowRuns to get
    :return: A list of WorkflowRuns
    """
    async with database.transaction():
        workflow = await _get_workflow(workflow, database)
        return await WorkflowRun.get_most_recent(database, workflow.metadata.name, n_rows=limit)


@tracer.start_as_current_span("get_workflow_run")
@inject_context
async def get_workflow_run(identifier: str | UUID, database: BaseStorage) -> WorkflowRun:
    """
    Get a WorkflowRun given an identifier.

    :param identifier: The identifier of the WorkflowRun to get
    :param database: The database to use
    :return: The WorkflowRun
    """
    async with database.transaction():
        run = await _get_workflow_run(identifier, database)
        if not run:
            raise ResourceNotFoundError
        return run


@tracer.start_as_current_span("delete_workflow_run")
@inject_context
async def delete_workflow_run(identifier: str | UUID, database: BaseStorage) -> WorkflowRun:
    """
    Delete a WorkflowRun given an identifier.

    :param identifier: The identifier of the WorkflowRun to delete
    :param database: The database to use
    :return: The deleted WorkflowRun
    """
    async with database.transaction():
        run = await _get_workflow_run(identifier, database)
        if not run:
            raise ResourceNotFoundError
        await run.delete(database)
        return run
