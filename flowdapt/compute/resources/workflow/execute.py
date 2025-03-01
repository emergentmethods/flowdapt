from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun, WorkflowRunState
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.resources.workflow.context import WorkflowRunContext


@asynccontextmanager
async def executor_lifespan(executor: Executor) -> AsyncIterator[Executor]:
    skip_lifespan = executor.running is True

    if not skip_lifespan:
        try:
            if not executor.running:
                await executor.start()
            yield executor
        finally:
            if executor.running:
                await executor.close()
    else:
        yield executor


async def execute_workflow(
    workflow: dict | WorkflowResource,
    input: dict = {},
    *,
    namespace: str = "default",
    return_result: bool = False,
    run: WorkflowRun | None = None,
    executor: Executor | None = None,
    config: dict = {},
    **params,
) -> WorkflowRun | Any:
    """
    Execute a Workflow locally for debugging purposes.

    :param workflow: Workflow definition in the form of a dictionary.
    :param input: Workflow input dictionary where keys are the parameters.
    :param namespace: Execution namespace, defaults to "default".
    :param return_result: Whether to return the result of the execution or the WorkflowRun.
    :param executor: Workflow executor, defaults to TestExecutor.
    :return: The result of the workflow execution.

    Example:
    ```python
    from flowdapt.compute.debug import execute_workflow

    example_workflow = {
        "name": "test",
        "stages": [
            {
                "name": "stage1",
                # We support passing a callable directly as a target for convenience
                # but you can still use an import string if needed.
                "target": lambda: list(range(10))
            },
            {
                "name": "stage2",
                "target": lambda x: x * 2,
                "depends_on": ["stage1"]
            }
        ]
    }

    workflow_run = await execute_workflow(example_workflow)
    # OR
    workflow_result = await execute_workflow(example_workflow, return_result=True)
    ```
    """
    from flowdapt.compute.executor.local import LocalExecutor

    if not executor:
        # Default to LocalExecutor if not specified. This is sufficient in most cases
        # since eager execution is preferred when debugging. Set processes to False
        # to default to a ThreadPoolExecutor instead.
        params["use_processes"] = params.get("use_processes", False)
        executor = LocalExecutor(**params)

    # Get a WorkflowResource instance from the workflow param if it's a dictionary
    if isinstance(workflow, dict):
        definition = WorkflowResource.model_validate(workflow)
    else:
        definition = workflow

    # Create a basic WorkflowRun, this is not persisted.
    run = (
        WorkflowRun(
            state=WorkflowRunState.running, workflow=definition.metadata.name, source="manual"
        )
        if not run
        else run
    )

    # Create a WorkflowRunContext for the stages to access in case they
    # use any of the information during execution.
    context = WorkflowRunContext(
        input=input,
        namespace=namespace,
        executor=executor.kind,
        run=run.model_copy(deep=True),
        definition=definition.model_copy(deep=True),
        config=config,
    )

    try:
        async with executor_lifespan(executor):
            # Finally, run the workflow using the Executor
            result = await executor(definition, run, context)
    except BaseException as e:
        # If an error occurs, set the WorkflowRun to failed and set the result
        # if return_result is True then raise the error as well.
        run.set_finished(
            (e.__class__.__name__, str(e)),
            WorkflowRunState.failed,
        )

        if return_result:
            raise e
    else:
        # If no error occurs, set the WorkflowRun to finished and set the result
        run.set_finished(
            result,
            WorkflowRunState.finished,
        )

    return result if return_result else run
