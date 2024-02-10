from flowdapt.compute.artifacts import Artifact
from flowdapt.compute.artifacts.misc import json_to_artifact, json_from_artifact
import pytest


@pytest.fixture(scope="function")
def artifact_params():
    return {"protocol": "memory", "base_path": "test"}


@pytest.fixture(scope="function")
def artifact(artifact_params):
    artifact = Artifact.new_artifact(
        name="test_artifact",
        **artifact_params
    )
    try:
        yield artifact
    finally:
        artifact.delete()


def test_json_to_artifact(artifact: Artifact):
    # Call json_to_artifact function
    json_to_artifact()(artifact, {"key": "value"})

    assert not artifact.is_empty, artifact.list_files()


def test_json_from_artifact(artifact: Artifact):
    # First, we'll need to save a JSON object to an artifact
    json_to_artifact()(artifact, {"key": "value"})

    # Then, we retrieve the JSON object
    retrieved_json = json_from_artifact()(artifact)

    # Assert that the original and retrieved JSON objects are equal
    assert retrieved_json == {"key": "value"}


def test_incorrect_load_hook_json(artifact: Artifact):
    # First, we'll need to save a JSON object to an artifact
    json_to_artifact()(artifact, {"key": "value"})

    # Then, we'll change the value_type to something other than "json"
    artifact["value_type"] = "object"

    # Then, we retrieve the JSON object
    with pytest.raises(AssertionError):
        json_from_artifact()(artifact)