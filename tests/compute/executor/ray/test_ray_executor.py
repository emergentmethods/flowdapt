import pytest
from flowdapt.compute.resources.workflow.execute import execute_workflow
from flowdapt.compute.executor.ray import RayExecutor, ExecuteStrategy


@pytest.mark.parametrize(
    "strategy",
    [
        ExecuteStrategy.ALL_AT_ONCE,
        ExecuteStrategy.GROUP_BY_GROUP,
    ]
)
async def test_ray_executor(strategy, example_workflow, example_workflow_expected_result):
    resources = {"mappers": 1}
    workflow_result = await execute_workflow(
        example_workflow,
        executor=RayExecutor(strategy=strategy, resources=resources),
        return_result=True
    )

    assert workflow_result == example_workflow_expected_result
