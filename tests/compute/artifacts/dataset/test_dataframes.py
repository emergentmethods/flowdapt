import pytest
import pandas

from flowdapt.lib.utils.misc import get_full_path_type
from flowdapt.compute.artifacts import Artifact
from flowdapt.compute.artifacts.dataset.dataframes import (
    dataframe_from_artifact,
    dataframe_to_artifact
)
from flowdapt.compute.object_store import default_load_hook
from tests.conftest import log_has_re

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


def test_dataframe_to_artifact(artifact: Artifact):
    df = pandas.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    })

    # Call dataframe_to_artifact function
    dataframe_to_artifact()(artifact, df)

    assert not artifact.is_empty, artifact.list_files()

    # Check the value_type metadata
    assert artifact["value_type"] == get_full_path_type(df)

def test_dataframe_from_artifact(artifact: Artifact):
    df = pandas.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    })

    # First, we'll need to save a dataframe to an artifact
    dataframe_to_artifact()(artifact, df)

    # Then, we retrieve the dataframe
    retrieved_df = dataframe_from_artifact()(artifact)

    # Assert that the original and retrieved dataframes are equal
    pandas.testing.assert_frame_equal(df, retrieved_df)


def test_dataframe_to_artifact_with_executor(artifact: Artifact):
    df = pandas.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    })

    # Call dataframe_to_artifact function with a specified executor
    dataframe_to_artifact(executor="executor1")(artifact, df)

    assert not artifact.is_empty, artifact.list_files()


def test_dataframe_from_artifact_with_executor(artifact: Artifact):
    df = pandas.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    })

    # First, we'll need to save a dataframe to an artifact
    dataframe_to_artifact(executor="executor1")(artifact, df)

    # Then, we retrieve the dataframe
    retrieved_df = dataframe_from_artifact(executor="executor1")(artifact)

    # Assert that the original and retrieved dataframes are equal
    pandas.testing.assert_frame_equal(df, retrieved_df)


def test_incorrect_load_hook_dataframe(artifact: Artifact, caplog):
    # First, we'll need to save a dataframe to an artifact
    df = pandas.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    })

    # save the dataframe to the artifact
    dataframe_to_artifact()(artifact, df)

    # next load the dataframe using the incorrect hook
    with pytest.raises(FileNotFoundError):
        default_load_hook()(artifact)
        assert log_has_re(r"default save hook", caplog), caplog