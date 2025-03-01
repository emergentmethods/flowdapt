from flowdapt.compute.cluster_memory.base import ClusterMemory
from flowdapt.lib.utils.misc import import_from_string


def get_cluster_memory_backend(backend: str, **kwargs) -> ClusterMemory:
    """
    Get the ClusterMemory object for the given backend.

    :param backend: Backend to get the ClusterMemory for.
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: ClusterMemory backend.
    """
    _backend_map = {
        "ray": "flowdapt.compute.executor.ray.cluster_memory.RayClusterMemory",
        "dask": "flowdapt.compute.executor.dask.cluster_memory.DaskClusterMemory",
        "local": "flowdapt.compute.executor.local.cluster_memory.LocalClusterMemory",
    }

    return import_from_string(_backend_map[backend])(**kwargs)
