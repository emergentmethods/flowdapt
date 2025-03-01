import pytest
import pandas
import numpy
import dask.array as da
import dask.dataframe as dd
from distributed import Client
from dask.datasets import timeseries
from pathlib import Path

from flowdapt.lib.utils.misc import get_full_path_type
from flowdapt.compute.artifacts import Artifact
from flowdapt.compute.artifacts.dataset.handler import get_handler_func
from flowdapt.compute.artifacts.dataset.arrays import (
    array_from_artifact,
    array_to_artifact,
)
from flowdapt.compute.artifacts.dataset.dataframes import (
    dataframe_from_artifact,
    dataframe_to_artifact,
)
from flowdapt.compute.executor.dask.collections import *


def _delete_folder_contents(folder_path):
    folder_path = Path(folder_path)

    # Delete all files and subdirectories within the folder
    for item in folder_path.glob('*'):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            _delete_folder_contents(item)  # Recursively delete subdirectories

    # Delete the folder itself
    folder_path.rmdir()


@pytest.fixture(scope='function', autouse=True)
def dask_local_cluster():
    # Starting local Dask cluster
    with Client() as client:
        yield client


@pytest.fixture
def artifact():
    # We need to use file protocol so the Dask workers can
    # have a chance to read files from the artifact
    artifact = Artifact.new_artifact(
        name="test_artifact",
        protocol="file",
        base_path="/tmp"
    )
    try:
        yield artifact
    finally:
        artifact.delete()

    _delete_folder_contents("/tmp/artifacts")

def test_handlers_are_registered():
    assert get_handler_func("dask", "dask.dataframe.core.DataFrame", "to_artifact") is not None
    assert get_handler_func("dask", "dask.dataframe.core.DataFrame", "from_artifact") is not None
    assert get_handler_func("dask", "dask.array.core.Array", "to_artifact") is not None
    assert get_handler_func("dask", "dask.array.core.Array", "from_artifact") is not None
    assert get_handler_func("dask", "dask_expr._collection.DataFrame", "to_artifact") is not None
    assert get_handler_func("dask", "dask_expr._collection.DataFrame", "from_artifact") is not None
    assert get_handler_func("dask", "dask.dataframe.dask_expr._collection.DataFrame", "to_artifact") is not None
    assert get_handler_func("dask", "dask.dataframe.dask_expr._collection.DataFrame", "from_artifact") is not None


def test_dask_array_to_artifact(artifact: Artifact, dask_local_cluster):
    array = da.random.random(100, 100)
    
    # Call array_to_artifact function
    array_to_artifact(executor="dask")(artifact, array)
    assert not artifact.is_empty, artifact.list_files()

    # Check the value_type metadata
    assert artifact["value_type"] == get_full_path_type(array)


def test_dask_array_from_artifact(artifact: Artifact, dask_local_cluster):
    array = da.random.random(100, 100)
    
    # First, we'll need to save an array to an artifact
    array_to_artifact(executor="dask")(artifact, array)

    # Then, we retrieve the array
    retrieved_array = array_from_artifact(executor="dask")(artifact)

    assert get_full_path_type(retrieved_array) == get_full_path_type(array)
    assert retrieved_array.shape == array.shape
    assert retrieved_array.dtype == array.dtype


def test_dask_df_to_artifact(artifact: Artifact, dask_local_cluster):
    df = timeseries()
    
    # Call array_to_artifact function
    dataframe_to_artifact(executor="dask")(artifact, df)
    assert not artifact.is_empty, artifact.list_files()

    # Check the value_type metadata
    assert artifact["value_type"] == get_full_path_type(df)


def test_dask_df_from_artifact(artifact: Artifact):
    df = timeseries()
    
    # First, we'll need to save an array to an artifact
    dataframe_to_artifact(executor="dask")(artifact, df)
    assert not artifact.is_empty, artifact.list_files()

    # Then, we retrieve the array
    retrieved_df = dataframe_from_artifact(executor="dask")(artifact)
    assert get_full_path_type(retrieved_df) == get_full_path_type(df)


def test_simple_collection_to_dask():
    # Test conversion with Pandas DataFrame
    pdf = pandas.DataFrame({'x': range(100), 'y': range(100, 200)})
    ddf = simple_collection_to_dask(pdf)
    assert isinstance(ddf, dd.DataFrame), "Converted object should be a Dask DataFrame"
    
    # Test conversion with Numpy array
    np_array = numpy.array([1, 2, 3, 4, 5])
    dask_array = simple_collection_to_dask(np_array)
    assert isinstance(dask_array, da.Array), "Converted object should be a Dask Array"

    # Test invalid input
    with pytest.raises(TypeError):
        simple_collection_to_dask("invalid input")


def test_simple_collection_from_dask():
    # Test conversion from Dask DataFrame
    pdf = pandas.DataFrame({'x': range(100), 'y': range(100, 200)})
    ddf = dd.from_pandas(pdf, npartitions=10)
    converted_df = simple_collection_from_dask(ddf)
    assert isinstance(converted_df, pandas.DataFrame), "Converted object should be a Pandas DataFrame"

    # Test conversion from Dask Array
    np_array = numpy.array([1, 2, 3, 4, 5])
    dask_array = da.from_array(np_array, chunks=2)
    converted_array = simple_collection_from_dask(dask_array)
    assert isinstance(converted_array, numpy.ndarray), "Converted object should be a Numpy Array"
    
    # Test invalid input
    with pytest.raises(TypeError):
        simple_collection_from_dask("invalid input")