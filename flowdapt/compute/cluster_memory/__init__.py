from typing import Any

from flowdapt.compute.cluster_memory.base import ClusterMemory
from flowdapt.compute.cluster_memory.utils import get_cluster_memory_backend


def _get_values_from_context(
    backend: str | None = None,
    namespace: str = "",
) -> tuple[str, str]:
    # If some values are not specified, get them from the current context
    from flowdapt.compute.resources.workflow.context import get_run_context
    current_context = get_run_context()

    namespace = namespace or current_context.namespace
    backend = backend or current_context.executor

    return backend, namespace


def put_in_cluster_memory(
    key: str,
    value: Any,
    *,
    namespace: str = "",
    backend: str | None = None,
    **kwargs
) -> None:
    """
    Put an object into the ClusterMemory.

    :param key: Key to put the object for.
    :type key: str
    :param value: Value to put.
    :type value: Any
    :param namespace: Namespace to put the object in, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to put the object in, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: None
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return _cluster_memory.put(key, value, namespace=namespace)


def get_from_cluster_memory(
    key: str,
    *,
    namespace: str = "",
    backend: str | None = None,
    **kwargs
) -> Any:
    """
    Get an object from the ClusterMemory.

    :param key: Key to get the object for.
    :type key: str
    :param namespace: Namespace to get the object from, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to get the object from, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: Value for the key
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return _cluster_memory.get(key, namespace=namespace)


def delete_from_cluster_memory(
    key: str,
    *,
    namespace: str = "",
    backend: str | None = None,
    **kwargs
) -> None:
    """
    Delete an object from the ClusterMemory.

    :param key: Key to delete the object for.
    :type key: str
    :param namespace: Namespace to delete the object from, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to delete the object from, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: None
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return _cluster_memory.delete(key, namespace=namespace)


__all__ = (
    "ClusterMemory",
    "get_cluster_memory_backend",
)
