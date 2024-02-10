from flowdapt.compute.resources.workflow.execute import execute_workflow
from flowdapt.compute.executor.local import LocalExecutor


async def test_local_executor(example_workflow, example_workflow_expected_result):
    workflow_result = await execute_workflow(
        example_workflow,
        executor=LocalExecutor(),
        return_result=True
    )

    assert workflow_result == example_workflow_expected_result

    workflow_result = await execute_workflow(
        example_workflow,
        executor=LocalExecutor(use_processes=False),
        return_result=True
    )

    assert workflow_result == example_workflow_expected_result