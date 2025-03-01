from typing import Any

from dask import compute, delayed
from dask.array import Array as DaskArray
from dask.array import concatenate as concatenate_arrays
from dask.array import from_array as from_numpy_array
from dask.array import from_delayed as from_delayed_array
from dask.dataframe import DataFrame as DaskDataFrame
from dask.dataframe import from_delayed as from_delayed_dataframe
from dask.dataframe import from_pandas as from_pandas_dataframe
from distributed import worker_client
from numpy import ndarray as NumpyArray
from pandas import DataFrame as PandasDataFrame

from flowdapt.compute.artifacts import Artifact
from flowdapt.compute.artifacts.dataset import register_handler
from flowdapt.compute.artifacts.dataset.arrays import (
    read_array_from_artifact,
    write_array_to_artifact,
)
from flowdapt.compute.artifacts.dataset.dataframes import (
    read_dataframe_from_artifact,
    write_dataframe_to_artifact,
)


def dask_dataframe_to_artifact(
    artifact: Artifact,
    dataframe: DaskDataFrame,
    format: str,
):
    """
    Persist a dask dataframe to an Artifact.

    :param artifact: The Artifact to persist the dataframe to.
    :param dataframe: The dask dataframe to persist to the Artifact.
    :param format: The format to use when persisting the dataframe.
    """
    if not isinstance(dataframe, DaskDataFrame):
        raise TypeError("`dataframe` must be a dask dataframe")

    # Partition the dataframe into delayed objects
    partitions = dataframe.to_delayed()
    # Wrap the write func into a dask delayed object so that it can be computed on the workers
    # Dask dataframes are simply a collection of pandas dataframes, so we can use the same write
    # function as we do for pandas dataframes
    write_func = delayed(write_dataframe_to_artifact, name="write-dataframe-to-artifact")

    # Call the write func for each partition and use a separate file to store them
    writes = []
    for i, part in enumerate(partitions):
        part_file = artifact.new_file(f"partition-{i}.{format}")

        writes.append(write_func(part_file, part, format))

    try:
        # Compute the writes on the cluster if we're on a worker
        with worker_client() as client:  # pragma: no cover
            client.compute(writes, sync=True)
    except ValueError:
        # We aren't on a worker so just call dask.compute
        compute(writes, sync=True)

    return artifact


def dask_dataframe_from_artifact(artifact: Artifact, format: str = "parquet", num_points: int = -1):
    """
    Get a dask dataframe from an Artifact.

    :param artifact: The Artifact to get the dataframe from.
    :param format: The format to use when reading the dataframe.
    :param num_points: The number of points to read from the dataframe.
    :return: A dask dataframe.
    """
    _valid_types = [
        "dask.dataframe.core.DataFrame",
        "dask.dataframe.core.Series",
        "dask_expr._collection.DataFrame",
        "dask.dataframe.dask_expr._collection.DataFrame",
    ]
    assert artifact["value_type"] in _valid_types, f"Artifact must be of type {_valid_types}"

    partition_files = artifact.list_files()
    read_func = delayed(read_dataframe_from_artifact, name="read-dataframe-from-artifact")

    reads = [read_func(file, format=format) for file in partition_files]

    dataframe = from_delayed_dataframe(reads)

    if num_points > 0:
        dataframe = dataframe.tail(num_points)

    return dataframe


def dask_array_to_artifact(
    artifact: Artifact,
    array: DaskArray,
    format: str = "npy",
    axis: int = 0,
) -> Artifact:
    """
    Persist a dask array to an Artifact.

    :param artifact: The Artifact to persist the array to.
    :param array: The dask array to persist to the Artifact.
    :param format: The format to use when persisting the array.
    :param axis: The axis to concatenate the partitions on.
    :return: The Artifact.
    """
    if not isinstance(array, DaskArray):
        raise TypeError("`array` must be a dask array")

    artifact["dtype"] = str(array.dtype)
    artifact["shape"] = array.shape
    artifact["chunks"] = array.chunks
    artifact["chunksize"] = array.chunksize
    artifact["axis"] = axis
    artifact["numblocks"] = array.numblocks
    artifact["blocksize"] = array.blocks[0].shape

    # array.to_delayed() returns a 2D array, containing the
    # delayed function called to create the sub arrays. Instead,
    # just serialize the blocks themselves in a delayed func.
    blocks = array.blocks.ravel()
    # Wrap the write func into a dask delayed object so that it can be computed on the workers
    write_func = delayed(write_array_to_artifact, name="write-array-to-artifact")

    # Call the write func for each partition and use a separate file to store them
    writes = []
    for i, part in enumerate(blocks):
        part_file = artifact.new_file(f"partition-{i}.{format}")

        writes.append(write_func(part_file, part, format))

    try:
        # Compute the writes on the cluster if we're on a worker
        with worker_client() as client:  # pragma: no cover
            client.compute(writes, sync=True)
    except ValueError:
        # We aren't on a worker so just call dask.compute
        compute(writes, sync=True)

    return artifact


def dask_array_from_artifact(artifact: Artifact, format: str = "npy"):
    """
    Get a dask array from an Artifact.

    :param artifact: The Artifact to get the array from.
    :param format: The format to use when reading the array.
    :return: A dask array.
    """
    assert artifact["value_type"] == "dask.array.core.Array", (
        "Artifact must have value_type 'dask.array.core.Array'"
    )

    partition_files = artifact.list_files()
    read_func = delayed(read_array_from_artifact, name="read-array-from-artifact")

    dtype = artifact["dtype"]
    axis = artifact["axis"]
    chunksize = artifact["chunksize"]

    reads = [read_func(file, format=format) for file in partition_files]
    partitions = [from_delayed_array(file, dtype=dtype, shape=chunksize) for file in reads]

    return concatenate_arrays(partitions, axis=axis)


def simple_collection_to_dask(value: Any, **kwargs):
    if isinstance(value, PandasDataFrame):
        return from_pandas_dataframe(value, npartitions=kwargs.pop("npartitions", 1), **kwargs)
    elif isinstance(value, NumpyArray):
        return from_numpy_array(value, **kwargs)

    raise TypeError(f"Cannot convert `{type(value)}` to a dask collection")


def simple_collection_from_dask(value: Any, **kwargs):
    if isinstance(value, DaskDataFrame):
        return value.compute(**kwargs)
    elif isinstance(value, DaskArray):
        return value.compute(**kwargs)

    raise TypeError(f"Cannot convert `{type(value)}` from a dask collection")


# Register dask collections handlers for Artifacts
register_handler("dask", "dask.dataframe.core.DataFrame", "to_artifact", dask_dataframe_to_artifact)
register_handler("dask", "dask.dataframe.core.Series", "to_artifact", dask_dataframe_to_artifact)
register_handler(
    "dask", "dask.dataframe.core.DataFrame", "from_artifact", dask_dataframe_from_artifact
)  # noqa: E501
register_handler(
    "dask", "dask.dataframe.core.Series", "from_artifact", dask_dataframe_from_artifact
)  # noqa: E501
register_handler("dask", "dask.array.core.Array", "to_artifact", dask_array_to_artifact)
register_handler("dask", "dask.array.core.Array", "from_artifact", dask_array_from_artifact)
register_handler(
    "dask", "dask_expr._collection.DataFrame", "to_artifact", dask_dataframe_to_artifact
)  # noqa: E501
register_handler(
    "dask", "dask_expr._collection.DataFrame", "from_artifact", dask_dataframe_from_artifact
)  # noqa: E501
register_handler(
    "dask",
    "dask.dataframe.dask_expr._collection.DataFrame",
    "to_artifact",
    dask_dataframe_to_artifact,
)  # noqa: E501
register_handler(
    "dask",
    "dask.dataframe.dask_expr._collection.DataFrame",
    "from_artifact",
    dask_dataframe_from_artifact,
)  # noqa: E501
