from typing import Any

import pandas

from flowdapt.compute.artifacts.dataset.handler import get_handler_func, register_handler
from flowdapt.compute.artifacts.dataset.utils import _get_current_executor, split_dataframe
from flowdapt.compute.artifacts.interface import Artifact, ArtifactFile
from flowdapt.lib.utils.misc import get_full_path_type


def read_dataframe_from_artifact(file: ArtifactFile, format: str = "parquet") -> pandas.DataFrame:
    """
    Read a dataframe from an ArtifactFile.

    :param file: The ArtifactFile to read the dataframe from.
    :param format: The format to use when reading the dataframe. Defaults to 'parquet'.
    :return: The dataframe read from the ArtifactFile.
    """
    read_format_map = {
        "parquet": pandas.read_parquet,
        "csv": pandas.read_csv,
        "orc": pandas.read_orc,
    }
    read_func = read_format_map[format]

    with file.open(mode="rb") as f:
        dataframe = read_func(f)

    return dataframe


def write_dataframe_to_artifact(
    file: ArtifactFile, dataframe: pandas.DataFrame, format: str = "parquet"
) -> None:
    """
    Write a dataframe to an ArtifactFile.

    :param file: The ArtifactFile to write the dataframe to.
    :param dataframe: The dataframe to write to the ArtifactFile.
    :param format: The format to use when writing the dataframe. Defaults to 'parquet'.
    :return: None
    """
    write_format_map = {"parquet": dataframe.to_parquet, "csv": dataframe.to_csv}
    write_func = write_format_map[format]

    with file.open(mode="wb") as f:
        write_func(f)

    return None


def pandas_dataframe_to_artifact(
    artifact: Artifact, value: Any, format: str = "parquet", num_parts: int = 1
) -> None:
    """
    Persist a pandas DataFrame to an Artifact.

    :param artifact: The Artifact to persist the dataframe to.
    :param value: The pandas DataFrame to persist to the Artifact.
    :param format: The format to use when persisting the dataframe. Defaults to 'parquet'.
    :param num_parts: The number of partitions to split the dataframe into. Defaults to 1.
    """
    # Check that the value is a pandas DataFrame
    assert isinstance(value, pandas.DataFrame), "Value must be a pandas DataFrame"

    partitions = split_dataframe(value, num_parts)

    for i, partition in enumerate(partitions):
        # When using pandas DataFrames just save as a single partition
        partition_file = artifact.new_file(f"partition-{i}.{format}")
        # Write it to the file
        write_dataframe_to_artifact(partition_file, partition, format=format)


def pandas_dataframe_from_artifact(artifact: Artifact, format: str = "parquet") -> pandas.DataFrame:
    """
    Get a pandas DataFrame from an Artifact.

    :param artifact: The Artifact to get the dataframe from.
    :param format: The format to use when getting the dataframe. Defaults to 'parquet'.
    :return: The pandas DataFrame read from the Artifact.
    """
    assert artifact["value_type"] == "pandas.core.frame.DataFrame", (
        "Artifact must have value_type 'pandas.core.frame.DataFrame'"
    )

    partitions = [
        read_dataframe_from_artifact(file, format=format)
        for file in artifact.list_files()
        if file.name.endswith(f".{format}")
    ]

    if not partitions:
        raise ValueError(
            f"Artifact '{artifact.name}' does not contain any files ending in '.{format}'"
        )

    return pandas.concat(partitions)


def dataframe_from_artifact(format: str = "parquet", *, executor: str = "", **kwargs):
    """
    Load a dataframe from an Artifact.

    :param format: The format to use when loading the dataframe. Defaults to 'parquet'.
    :param executor: The executor to use when loading the dataframe. Defaults to the current
    executor.
    :return: A function that takes an artifact and returns a dataframe.

    Example:
        >>> my_dataframe = dataframe_from_artifact(format="csv")(artifact)
    """
    # If not specified, get the currente executor from the run context
    if not executor:
        executor = _get_current_executor() or "*"

    def _(artifact: Artifact):
        value_type = artifact["value_type"]
        # Get the handler function given the executor, type of value, and operation
        handler = get_handler_func(executor, value_type, "from_artifact")
        # Call the handler function with the artifact, value, and any kwargs
        return handler(artifact, format=format, **kwargs)

    return _


def dataframe_to_artifact(format: str = "parquet", *, executor: str = "", **kwargs):
    """
    Persist a dataframe to an Artifact.

    :param format: The format to use when persisting the dataframe. Defaults to 'parquet'.
    :param executor: The executor to use when persisting the dataframe. Defaults to the current
    executor.
    :return: A function that takes an artifact and a dataframe, and persists the dataframe to the
    artifact.

    Example:
        >>> dataframe_to_persist = pd.DataFrame(...)
        >>> dataframe_to_artifact(format="csv")(artifact, dataframe_to_persist)
    """
    # If not specified, get the currente executor from the run context
    if not executor:
        executor = _get_current_executor() or "*"

    def _(artifact: Artifact, value: Any):
        # Make sure the Artifact is cleared before writing
        artifact.clear()

        # Get the full type of the value
        value_type = get_full_path_type(value)

        # Get the handler function given the executor, type of value, and operation
        handler = get_handler_func(executor, value_type, "to_artifact")

        # Set the value type on the artifact to recreate the dataframe when the artifact is loaded
        artifact["value_type"] = value_type

        # Call the handler function with the artifact, value, and any kwargs
        return handler(artifact, value, format=format, **kwargs)

    return _


register_handler("*", "pandas.core.frame.DataFrame", "to_artifact", pandas_dataframe_to_artifact)
register_handler(
    "*", "pandas.core.frame.DataFrame", "from_artifact", pandas_dataframe_from_artifact
)  # noqa: E501
