from flowdapt.compute.cluster_memory.base import ClusterMemory
from flowdapt.lib.utils.misc import import_from_string

_backend_map = {
    "ray": "flowdapt.compute.executor.ray.cluster_memory.RayClusterMemory",
    "dask": "flowdapt.compute.executor.dask.cluster_memory.DaskClusterMemory",
    "local": "flowdapt.compute.executor.local.cluster_memory.LocalClusterMemory",
}

# Module-level cache: one ClusterMemory instance per (backend, kwargs) combination.
# In Ray workers each process has its own module state, so this is per-worker-process —
# meaning ray.get_actor() is paid once at first use, not on every put/get call.
_instances: dict[str, ClusterMemory] = {}


def get_cluster_memory_backend(backend: str, **kwargs) -> ClusterMemory:
    """
    Get the ClusterMemory object for the given backend.

    :param backend: Backend to get the ClusterMemory for.
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: ClusterMemory backend.
    """
    key = f"{backend}:{tuple(sorted(kwargs.items()))}"
    if key not in _instances:
        _instances[key] = import_from_string(_backend_map[backend])(**kwargs)
    return _instances[key]
