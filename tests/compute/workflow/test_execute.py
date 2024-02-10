from datetime import datetime
from uuid import UUID

from flowdapt.compute.resources.workflow.execute import execute_workflow


async def test_execute_workflow(example_workflow):
    workflow_run = await execute_workflow(example_workflow)

    assert workflow_run.finished_at is not None, workflow_run
    assert workflow_run.state == "finished", workflow_run
    assert workflow_run.result == [0, 1, 4, 9, 16, 25, 36, 49, 64, 81], workflow_run
    assert isinstance(workflow_run.started_at, datetime), workflow_run
    assert isinstance(workflow_run.uid, UUID), workflow_run
    assert isinstance(workflow_run.name, str), workflow_run


async def test_execute_workflow_with_input(example_workflow):
    example_workflow["spec"]["stages"][0]["target"] = lambda test: list(range(len(test)))
    example_workflow["spec"]["stages"].pop(1)

    workflow_run = await execute_workflow(example_workflow, input={"test": "value"})

    assert workflow_run.finished_at is not None, workflow_run
    assert workflow_run.state == "finished", workflow_run
    assert len(workflow_run.result) == len("value"), workflow_run
    assert isinstance(workflow_run.started_at, datetime), workflow_run
    assert isinstance(workflow_run.uid, UUID), workflow_run
    assert isinstance(workflow_run.name, str), workflow_run


async def test_execute_workflow_result(example_workflow):
    workflow_result = await execute_workflow(example_workflow, return_result=True)

    assert workflow_result == [0, 1, 4, 9, 16, 25, 36, 49, 64, 81], workflow_result

    workflow_run = await execute_workflow(example_workflow, return_result=False)

    assert workflow_run.finished_at is not None, workflow_run
    assert workflow_run.state == "finished", workflow_run
    assert workflow_run.result == [0, 1, 4, 9, 16, 25, 36, 49, 64, 81], workflow_run
    assert isinstance(workflow_run.started_at, datetime), workflow_run
    assert isinstance(workflow_run.uid, UUID), workflow_run
    assert isinstance(workflow_run.name, str), workflow_run


async def test_execute_workflow_simple_stage():
    workflow_run = await execute_workflow(
        {
            "metadata": {
                "name": "test",
            },
            "spec": {
                "stages": [
                    {"name": "stage1", "type": "simple", "target": lambda: True}
                ]
            }
        }
    )

    assert workflow_run.result == True, workflow_run


async def test_execute_workflow_parameterized_stage():
    # Test a parameterized stage
    workflow_run = await execute_workflow(
        {
            "metadata": {
                "name": "test",
            },
            "spec": {
                "stages": [
                    {
                        "name": "stage1",
                        "target": lambda: list(range(4)),
                    },
                    {
                        "name": "stage2",
                        "target": lambda x: x * 2,
                        "depends_on": ["stage1"],
                        "type": "parameterized"
                    }        
                ]
            }
        }
    )

    assert workflow_run.result == [0, 2, 4, 6], workflow_run
    assert workflow_run.state == "finished", workflow_run
    assert workflow_run.finished_at is not None, workflow_run

    # Test a parameterized stage mapping on an input value
    # In this case if the parameterized stage was after another, it would
    # map on the input value instead of the return value of the previous stage.
    # Since it's the first stage, the map on has to be the same name as the
    # parameter.
    # TODO: Figure out a way to make this more flexible when it's the first stage
    workflow_run = await execute_workflow(
        {
            "metadata": {
                "name": "test",
            },
            "spec": {
                "stages": [
                    {
                        "name": "stage1",
                        "target": lambda x: x * 2,
                        "type": "parameterized",
                        "options": {
                            "map_on": "x"
                        }
                    }
                ]
            }
        },
        input={"x": [1, 2]}
    )

    assert workflow_run.result == [2, 4], workflow_run