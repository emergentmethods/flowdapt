from flowdapt.compute.resources.workflow.execute import execute_workflow
from flowdapt.compute.executor.dask import DaskExecutor


async def test_dask_executor(example_workflow, example_workflow_expected_result):
    workflow_result = await execute_workflow(
        example_workflow,
        executor=DaskExecutor(),
        return_result=True
    )

    assert workflow_result == example_workflow_expected_result