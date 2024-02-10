import pytest
import numpy

from flowdapt.lib.utils.misc import get_full_path_type
from flowdapt.compute.artifacts import Artifact
from flowdapt.compute.artifacts.dataset.arrays import (
    array_from_artifact,
    array_to_artifact
)


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


def test_array_to_artifact(artifact: Artifact):
    array = numpy.random.rand(100, 100)
    
    # Call array_to_artifact function
    array_to_artifact()(artifact, array)
    assert not artifact.is_empty, artifact.list_files()

    # Check the value_type metadata
    assert artifact["value_type"] == get_full_path_type(array)


def test_array_from_artifact(artifact: Artifact):
    array = numpy.random.rand(100, 100)
    
    # First, we'll need to save an array to an artifact
    array_to_artifact()(artifact, array)

    # Then, we retrieve the array
    retrieved_array = array_from_artifact()(artifact)

    # Assert that the original and retrieved arrays are equal
    numpy.testing.assert_array_equal(array, retrieved_array)


def test_array_to_artifact_with_executor(artifact: Artifact):
    array = numpy.random.rand(100, 100)
    
    # Call array_to_artifact function with a specified executor
    array_to_artifact(executor="executor1")(artifact, array)

    assert not artifact.is_empty, artifact.list_files()


def test_array_from_artifact_with_executor(artifact: Artifact):
    array = numpy.random.rand(100, 100)
    
    # First, we'll need to save an array to an artifact
    array_to_artifact(executor="executor1")(artifact, array)

    # Then, we retrieve the array
    retrieved_array = array_from_artifact(executor="executor1")(artifact)

    # Assert that the original and retrieved arrays are equal
    numpy.testing.assert_array_equal(array, retrieved_array)