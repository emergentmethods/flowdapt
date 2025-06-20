import pytest

from flowdapt.compute.resources.workflow.execute import execute_workflow
from flowdapt.compute.object_store import put, get, exists
from flowdapt.compute.artifacts import list_artifacts


@pytest.fixture(scope="function")
def mocked_artifacts_values(mocker):
    # Mock the values returned by _get_values_from_context for Artifacts
    # so we use the memory backend
    mock_context_values = mocker.patch("flowdapt.compute.artifacts._get_values_from_context")
    mock_context_values.return_value = ("default", "memory", "", {})

    return mock_context_values


@pytest.fixture
def test_workflow():
    return {
        "metadata": {
            "name": "test",
        },
        "spec": {
            "stages": [
                {
                    "name": "stage1",
                    "target": lambda: put("test", 1)
                },
                {
                    "name": "stage2",
                    "target": lambda stage_one: get("test"),
                    "depends_on": ["stage1"]
                },
            ]
        }
    }


async def test_object_store_put_get(mocked_artifacts_values, test_workflow):
    workflow_result = await execute_workflow(test_workflow, return_result=True)
    assert workflow_result == 1, workflow_result


async def test_object_store_put_get_fallback(mocked_artifacts_values, test_workflow, mocker, caplog):
    mock_cm_put = mocker.patch("flowdapt.compute.object_store.put_in_cluster_memory")
    mock_cm_put.side_effect = Exception("CM PUT FAILED")

    mock_cm_get = mocker.patch("flowdapt.compute.object_store.get_from_cluster_memory")
    mock_cm_get.side_effect = Exception("CM GET FAILED")

    workflow_run = await execute_workflow(test_workflow)
    assert len(list_artifacts()) == 1, list_artifacts()
