from typing import Any

from distributed import get_client

from flowdapt.compute.cluster_memory.base import ClusterMemory
from flowdapt.compute.executor.dask.collections import (
    DaskArray,
    DaskDataFrame,
    NumpyArray,
    PandasDataFrame,
    simple_collection_from_dask,
    simple_collection_to_dask,
)
from flowdapt.lib.utils.misc import get_full_path_type


# TODO: Dask's Actor API is incredibly lack luster. It's not possible to get a ref to an Actor
# that's been submitted from a different client. Also Dask does not submit Actor's to each worker
# like Ray does, and we can't use an actor per worker to keep shared memory between all
# workers. Until that can change, DaskClusterMemory only supports dask collections and their
# simpler types. This also means namespaces are directly prepended to the key instead of
# keeping the data separate.
class DaskClusterMemory(ClusterMemory):
    def __init__(self):
        self.client = get_client()

    def get(self, key: str, *, namespace: str = "default") -> Any:
        full_key = f"{namespace}__{key}"
        # Get the collection from the scheduler and the type from the task
        # metadata to recreate it if it's not supposed to be a dask collection
        value = self.client.get_dataset(full_key)
        value_type = self.client.get_metadata(f"{full_key}__type")

        if value_type in [
            get_full_path_type(PandasDataFrame),
            get_full_path_type(NumpyArray),
        ]:
            # Convert the dask collection to its simpler type
            value = simple_collection_from_dask(value)

        return value

    def put(self, key: str, value: Any, *, namespace: str = "default"):
        # We expect only dask collections or their simpler types to be passed in
        if not isinstance(value, (DaskDataFrame, DaskArray, PandasDataFrame, NumpyArray)):
            raise ValueError(
                f"Only dask collections or their simpler types are supported, got `{type(value)}`"
            )
        full_key = f"{namespace}__{key}"
        value_type = get_full_path_type(value)

        # Check if it exists first, if so delete so we can overwrite it
        if full_key in self.client.list_datasets():
            self.delete(key, namespace=namespace)

        if value_type == get_full_path_type(PandasDataFrame):
            # We need to convert to a dask dataframe from pandas, only 1 partition since
            # it's expected to be in memory
            value = simple_collection_to_dask(value, npartitions=1)
        elif value_type == get_full_path_type(NumpyArray):
            # We need to convert to a dask array from numpy
            value = simple_collection_to_dask(value)

        # Publish it to the scheduler
        self.client.publish_dataset(value, name=full_key)
        # Set metadata on the scheduler about type so we know how to recreate it
        self.client.set_metadata(f"{full_key}__type", value_type)

    def delete(self, key: str, *, namespace: str = "default"):
        full_key = f"{namespace}__{key}"
        self.client.unpublish_dataset(full_key)
        # Not sure how else to delete metadata for a certain key
        self.client.set_metadata(f"{full_key}__type", "")

    def clear(self, namespace: str | None = None) -> None:
        for dataset in self.client.list_datasets():
            if namespace:
                # Only delete datasets that match the namespace
                if not dataset.startswith(f"{namespace}__"):
                    continue

            self.client.unpublish_dataset(dataset)
            # Not sure how else to delete metadata for a certain key
            self.client.set_metadata(f"{dataset}__type", "")

    async def aget(self, key: str, *, namespace: str = "default") -> Any:
        raise NotImplementedError(
            "DaskClusterMemory does not support async operations. "
            "Use the synchronous methods instead."
        )

    async def aput(self, key: str, value: Any, *, namespace: str = "default") -> None:
        raise NotImplementedError(
            "DaskClusterMemory does not support async operations. "
            "Use the synchronous methods instead."
        )

    async def adelete(self, key: str, *, namespace: str = "default") -> None:
        raise NotImplementedError(
            "DaskClusterMemory does not support async operations. "
            "Use the synchronous methods instead."
        )

    async def alist(self, prefix: str | None = None, *, namespace: str = "default") -> list[str]:
        raise NotImplementedError(
            "DaskClusterMemory does not support async operations. "
            "Use the synchronous methods instead."
        )

    async def aexists(self, key: str, *, namespace: str = "default") -> bool:
        raise NotImplementedError(
            "DaskClusterMemory does not support async operations. "
            "Use the synchronous methods instead."
        )

    async def aclear(self, *, namespace: str | None = None) -> None:
        raise NotImplementedError(
            "DaskClusterMemory does not support async operations. "
            "Use the synchronous methods instead."
        )
