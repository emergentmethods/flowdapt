from typing import Any

from flowdapt.compute.cluster_memory.base import ClusterMemory
from flowdapt.compute.cluster_memory.utils import get_cluster_memory_backend


def _get_values_from_context(
    backend: str | None = None,
    namespace: str | None = None,
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
    namespace: str | None = None,
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


async def aput_in_cluster_memory(
    key: str,
    value: Any,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> None:
    """
    Asynchronously put an object into the ClusterMemory

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
    return await _cluster_memory.aput(key, value, namespace=namespace)


def get_from_cluster_memory(
    key: str,
    *,
    namespace: str | None = None,
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


async def aget_from_cluster_memory(
    key: str,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> Any:
    """
    Asynchronously get an object from the ClusterMemory.

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
    return await _cluster_memory.aget(key, namespace=namespace)


def delete_from_cluster_memory(
    key: str,
    *,
    namespace: str | None = None,
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


async def adelete_from_cluster_memory(
    key: str,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> None:
    """
    Asynchronously delete an object from the ClusterMemory.

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
    return await _cluster_memory.adelete(key, namespace=namespace)


def list_cluster_memory(
    prefix: str | None = None,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> list[str]:
    """
    List all keys in the ClusterMemory for a given namespace.

    :param prefix: Optional prefix to filter the keys by.
    :type prefix: str | None, optional
    :param namespace: Namespace to list the keys from, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to list the keys from, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: List of keys in the ClusterMemory for the given namespace.
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return _cluster_memory.list(prefix, namespace=namespace)


async def alist_cluster_memory(
    prefix: str | None = None,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> list[str]:
    """
    Asynchronously list all keys in the ClusterMemory for a given namespace.

    :param prefix: Optional prefix to filter the keys by.
    :type prefix: str | None, optional
    :param namespace: Namespace to list the keys from, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to list the keys from, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: List of keys in the ClusterMemory for the given namespace.
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return await _cluster_memory.alist(prefix, namespace=namespace)


def exists_in_cluster_memory(
    key: str,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> bool:
    """
    Check if a key exists in the ClusterMemory.

    :param key: Key to check for existence.
    :type key: str
    :param namespace: Namespace to check the key in, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to check the key in, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: True if the key exists, False otherwise.
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return _cluster_memory.exists(key, namespace=namespace)


async def aexists_in_cluster_memory(
    key: str,
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> bool:
    """
    Asynchronously check if a key exists in the ClusterMemory.

    :param key: Key to check for existence.
    :type key: str
    :param namespace: Namespace to check the key in, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to check the key in, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: True if the key exists, False otherwise.
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return await _cluster_memory.aexists(key, namespace=namespace)


def clear_cluster_memory(
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> None:
    """
    Clear all keys in the ClusterMemory for a given namespace.

    :param namespace: Namespace to clear the keys from, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str, optional
    :param backend: Backend to clear the keys from, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: None
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return _cluster_memory.clear(namespace=namespace)


async def aclear_cluster_memory(
    *,
    namespace: str | None = None,
    backend: str | None = None,
    **kwargs
) -> None:
    """
    Asynchronously clear all keys in the ClusterMemory for a given namespace.

    :param namespace: Namespace to clear the keys from, defaults to the namespace of the current
    WorkflowRunContext.
    :type namespace: str | None, optional
    :param backend: Backend to clear the keys from, if not specified it will be inferred from the
    current WorkflowRunContext.
    :type backend: str | None, optional
    :param kwargs: Keyword arguments to pass to the ClusterMemory backend.
    :return: None
    """
    backend, namespace = _get_values_from_context(backend, namespace)
    _cluster_memory = get_cluster_memory_backend(backend, **kwargs)
    return await _cluster_memory.aclear(namespace=namespace)


__all__ = (
    "ClusterMemory",
    "get_cluster_memory_backend",
    "put_in_cluster_memory",
    "aput_in_cluster_memory",
    "get_from_cluster_memory",
    "aget_from_cluster_memory",
    "delete_from_cluster_memory",
    "adelete_from_cluster_memory",
    "list_cluster_memory",
    "alist_cluster_memory",
    "exists_in_cluster_memory",
    "aexists_in_cluster_memory",
    "clear_cluster_memory",
    "aclear_cluster_memory",
)
