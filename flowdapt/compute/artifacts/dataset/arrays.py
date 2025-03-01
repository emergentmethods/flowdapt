from typing import Any, Callable

import numpy

from flowdapt.compute.artifacts import Artifact, ArtifactFile
from flowdapt.compute.artifacts.dataset.handler import get_handler_func, register_handler
from flowdapt.compute.artifacts.dataset.utils import _get_current_executor
from flowdapt.lib.utils.misc import get_full_path_type


def read_array_from_artifact(artifact_file: ArtifactFile, format: str = "npy"):
    read_format_map = {"npy": numpy.load, "npz": numpy.load, "pickle": numpy.load}
    read_func = read_format_map[format]

    with artifact_file.open(mode="rb") as file:
        array = read_func(file, allow_pickle=True)

    return array


def write_array_to_artifact(file: ArtifactFile, array: numpy.ndarray, format: str = "npy"):
    write_format_map = {"npy": numpy.save}
    write_func = write_format_map[format]

    with file.open(mode="wb") as f:
        write_func(f, array)

    return None


def numpy_array_to_artifact(
    artifact: Artifact, value: Any, format: str = "npy", num_parts: int = 1
) -> None:
    """
    Persist a numpy array to an Artifact.

    :param artifact: The Artifact to persist the array to.
    :param value: The numpy array to persist to the Artifact.
    :param format: The format to use when persisting the array. Defaults to 'npy'.
    :param num_parts: The number of partitions to split the array into. Defaults to 1.
    """
    # Check that the value is a numpy array
    assert isinstance(value, numpy.ndarray), "Value must be a numpy array"

    partitions = numpy.array_split(value, num_parts)

    for i, partition in enumerate(partitions):
        # When using numpy arrays just save as a single partition
        partition_file = artifact.new_file(f"partition-{i}.{format}")
        # Write it to the file
        write_array_to_artifact(partition_file, partition, format=format)


def numpy_array_from_artifact(artifact: Artifact, format: str = "npy") -> numpy.ndarray:
    """
    Get a numpy array from an Artifact.

    :param artifact: The Artifact to get the array from.
    :param format: The format to use when getting the array. Defaults to 'npy'.
    :return: The numpy array read from the Artifact.
    """
    assert artifact["value_type"] == "numpy.ndarray", (
        "Artifact must have value_type 'numpy.ndarray'"
    )

    partitions = [
        read_array_from_artifact(file, format=format)
        for file in artifact.list_files()
        if file.name.endswith(f".{format}")
    ]

    if not partitions:
        raise ValueError(
            f"Artifact '{artifact.name}' does not contain any files ending in '.{format}'"
        )

    return numpy.concatenate(partitions)


def array_to_artifact(
    format: str = "npy", *, executor: str = "", **kwargs
) -> Callable[[Artifact, Any], None]:
    """
    Persist an array to an Artifact.

    :param format: The format to use when persisting the array. Defaults to 'npy'.
    :param executor: The executor to use when persisting the array. Defaults to the
    current executor.
    :param kwargs: Additional keyword arguments to pass to the handler function.
    :return: A function that persists an array to an Artifact.

    Example:
        >>> array_to_artifact(format="npy")(artifact, array)
    """
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


def array_from_artifact(
    format: str = "npy", *, executor: str = "", **kwargs
) -> Callable[[Artifact], numpy.ndarray]:
    """
    Get an array from an Artifact.

    :param format: The format to use when getting the array. Defaults to 'npy'.
    :param executor: The executor to use when getting the array. Defaults to the
    current executor.
    :param kwargs: Additional keyword arguments to pass to the handler function.
    :return: A function that gets an array from an Artifact.

    Example:
        >>> array = array_from_artifact(format="npy")(artifact)
    """
    if not executor:
        executor = _get_current_executor() or "*"

    def _(artifact: Artifact):
        value_type = artifact["value_type"]
        # Get the handler function given the executor, type of value, and operation
        handler = get_handler_func(executor, value_type, "from_artifact")

        # Call the handler function with the artifact and any kwargs
        return handler(artifact, format=format, **kwargs)

    return _


register_handler("*", "numpy.ndarray", "to_artifact", numpy_array_to_artifact)
register_handler("*", "numpy.ndarray", "from_artifact", numpy_array_from_artifact)
