from enum import Enum
from typing import Any, Awaitable, Callable, Type, TypeAlias

from flowdapt.compute.artifacts import (
    Artifact,
    aclear_artifacts,
    adelete_artifact,
    aget_artifact,
    alist_artifacts,
    clear_artifacts,
    delete_artifact,
    get_artifact,
    list_artifacts,
)
from flowdapt.compute.cluster_memory import (
    aclear_cluster_memory,
    adelete_from_cluster_memory,
    aexists_in_cluster_memory,
    aget_from_cluster_memory,
    alist_cluster_memory,
    aput_in_cluster_memory,
    clear_cluster_memory,
    delete_from_cluster_memory,
    exists_in_cluster_memory,
    get_from_cluster_memory,
    list_cluster_memory,
    put_in_cluster_memory,
)
from flowdapt.lib.config import get_configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.serializers import CloudPickleSerializer, Serializer


logger = get_logger(__name__)


ArtifactSaveHook: TypeAlias = Callable[[Artifact, Any], Any]
ArtifactLoadHook: TypeAlias = Callable[[Artifact], Any]
AsyncArtifactSaveHook: TypeAlias = Callable[[Artifact, Any], Awaitable[Any]]
AsyncArtifactLoadHook: TypeAlias = Callable[[Artifact], Awaitable[Any]]


class Strategy(str, Enum):
    """
    The strategy to use for storing/retrieving objects in the object store.
    """
    # Fallback first attempts cluster memory, and if it fails, falls back to
    # storing the object in an Artifact.
    FALLBACK = "fallback"
    # Only store the object in an Artifact.
    ARTIFACT = "artifact"
    # Only store the object in cluster memory.
    CLUSTER_MEMORY = "cluster_memory"


def default_save_hook(
    serializer: Type[Serializer] | Serializer = CloudPickleSerializer
) -> ArtifactSaveHook:
    """
    The default save hook for objects.

    This will serialize the object using the given serializer and save it to the
    Artifact under the `object` file.
    """

    def _inner(artifact: Artifact, value: Any):
        artifact["value_type"] = "object"
        serialized = serializer.dumps(value)
        obj_file = artifact.get_file("object", create=True)
        obj_file.write(serialized)

    return _inner


def default_load_hook(
    serializer: type[Serializer] | Serializer = CloudPickleSerializer
) -> ArtifactLoadHook:
    """
    The default load hook for objects.

    This will load the object from the Artifact under the `object` file and
    deserialize it using the given serializer.
    """

    def _inner(artifact: Artifact):
        if artifact["value_type"] != "object":
            logger.warning(
                "ArtifactHookMismatchWarning",
                artifact=artifact.name,
                namespace=artifact.namespace,
                old=artifact["value_type"],
                new="object",
            )
        try:
            obj_file = artifact.get_file("object")
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Artifact {artifact} has no `object` file. It is likely the Artifact has been "
                "corrupted or it was not saved with the default save hook."
            ) from e

        return serializer.loads(obj_file.read(mode="rb"))

    return _inner


def default_async_save_hook(
    serializer: Type[Serializer] | Serializer = CloudPickleSerializer
) -> AsyncArtifactSaveHook:
    """
    The default asynchronous save hook for objects.

    This will serialize the object using the given serializer and save it to the
    Artifact under the `object` file.
    """
    async def _inner(artifact: Artifact, value: Any):
        artifact["value_type"] = "object"
        serialized = serializer.dumps(value)
        obj_file = await artifact.aget_file("object", create=True)
        await obj_file.awrite(serialized)

    return _inner


def default_async_load_hook(
    serializer: Type[Serializer] | Serializer = CloudPickleSerializer
) -> AsyncArtifactLoadHook:
    """
    The default asynchronous load hook for objects.

    This will load the object from the Artifact under the `object` file and
    deserialize it using the given serializer.
    """

    async def _inner(artifact: Artifact):
        if artifact["value_type"] != "object":
            logger.warning(
                "ArtifactHookMismatchWarning",
                artifact=artifact.name,
                namespace=artifact.namespace,
                old=artifact["value_type"],
                new="object",
            )
        try:
            obj_file = await artifact.aget_file("object")
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Artifact {artifact} has no `object` file. It is likely the Artifact has been "
                "corrupted or it was not saved with the default save hook."
            ) from e

        return serializer.loads(await obj_file.aread(mode="rb"))

    return _inner


def put_object(
    key: str,
    value: Any,
    *,
    namespace: str | None = None,
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    save_artifact_hook: ArtifactSaveHook = default_save_hook(),  # noqa: B008
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> None:
    """
    Put an object into the object store.

    This will attempt to put the object into cluster memory first, and if that fails
    will fallback to storing the object in an Artifact with the given key.

    :param key: The key to store the object under.
    :type key: str
    :param value: The object to store.
    :type value: Any
    :param namespace: The namespace to store the object under, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param artifact_only: If True, the strategy will be set to Artifact. *Deprecated* Use
    the `strategy` parameter instead.
    :type artifact_only: bool
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param save_artifact_hook: A callable that takes an Artifact and a value and saves
    the value to the Artifact.
    :type save_artifact_hook: ArtifactSaveHook
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: None
    :rtype: None
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if artifact_only:
        logger.warning(
            "DeprecationWarning",
            message=(
                "The `artifact_only` parameter is deprecated and will be removed in a "
                "future version. Use the `strategy` parameter instead."
            ),
        )
        strategy = Strategy.ARTIFACT

    if strategy != Strategy.ARTIFACT:
        try:
            return put_in_cluster_memory(
                key=key,
                value=value,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = get_artifact(
        name=key,
        namespace=namespace,
        create=True,
        **(artifact_params or {}),
    )
    save_artifact_hook(_artifact, value)
    return


async def aput_object(
    key: str,
    value: Any,
    *,
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    save_artifact_hook: AsyncArtifactSaveHook = default_async_save_hook(),  # noqa: B008
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> None:
    """
    Put an object into the object store.

    This will attempt to put the object into cluster memory first, and if that fails
    will fallback to storing the object in an Artifact with the given key.

    :param key: The key to store the object under.
    :type key: str
    :param value: The object to store.
    :type value: Any
    :param namespace: The namespace to store the object under, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param save_artifact_hook: A callable that takes an Artifact and a value and saves
    the value to the Artifact.
    :type save_artifact_hook: AsyncArtifactSaveHook
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: None
    :rtype: None
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return await aput_in_cluster_memory(
                key=key,
                value=value,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = await aget_artifact(
        name=key,
        namespace=namespace,
        create=True,
        **(artifact_params or {}),
    )
    await save_artifact_hook(_artifact, value)


def get_object(
    key: str,
    *,
    namespace: str | None = None,
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    load_artifact_hook: ArtifactLoadHook = default_load_hook(),  # noqa: B008
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> Any:
    """
    Get an object from the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to get the object from.
    :type key: str
    :param namespace: The namespace to get the object from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param artifact_only: If True, the strategy will be set to Artifact. *Deprecated* Use
    the `strategy` parameter instead.
    :type artifact_only: bool
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param load_artifact_hook: A callable that takes an Artifact and returns the value
    stored in the Artifact.
    :type load_artifact_hook: ArtifactLoadHook
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: The object stored under the given key.
    :rtype: Any
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if artifact_only:
        logger.warning(
            "DeprecationWarning",
            message=(
                "The `artifact_only` parameter is deprecated and will be removed in a "
                "future version. Use the `strategy` parameter instead."
            ),
        )
        strategy = Strategy.ARTIFACT

    if strategy != Strategy.ARTIFACT:
        try:
            return get_from_cluster_memory(
                key=key,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = get_artifact(
        name=key,
        namespace=namespace,
        **(artifact_params or {})
    )
    return load_artifact_hook(_artifact)


async def aget_object(
    key: str,
    *,
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    load_artifact_hook: AsyncArtifactLoadHook = default_async_load_hook(),  # noqa: B008
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> Any:
    """
    Get an object from the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to get the object from.
    :type key: str
    :param namespace: The namespace to get the object from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param load_artifact_hook: A callable that takes an Artifact and returns the value
    stored in the Artifact.
    :type load_artifact_hook: AsyncArtifactLoadHook
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: The object stored under the given key.
    :rtype: Any
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return await aget_from_cluster_memory(
                key=key,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = await aget_artifact(
        name=key,
        namespace=namespace,
        **(artifact_params or {}),
    )
    return await load_artifact_hook(_artifact)


def delete_object(
    key: str,
    *,
    namespace: str | None = None,
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> None:
    """
    Delete an object from the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to get the object from.
    :type key: str
    :param namespace: The namespace to get the object from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param artifact_only: If True, the strategy will be set to Artifact. *Deprecated* Use
    the `strategy` parameter instead.
    :type artifact_only: bool
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param load_artifact_hook: A callable that takes an Artifact and returns the value
    stored in the Artifact.
    :type load_artifact_hook: ArtifactLoadHook
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: None
    :rtype: None
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if artifact_only:
        logger.warning(
            "DeprecationWarning",
            message=(
                "The `artifact_only` parameter is deprecated and will be removed in a "
                "future version. Use the `strategy` parameter instead."
            ),
        )
        strategy = Strategy.ARTIFACT

    if strategy != Strategy.ARTIFACT:
        try:
            return delete_from_cluster_memory(
                key=key,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    return delete_artifact(
        name=key,
        namespace=namespace,
        **(artifact_params or {}),
    )


async def adelete_object(
    key: str,
    *,
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> Any:
    """
    Delete an object from the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to get the object from.
    :type key: str
    :param namespace: The namespace to get the object from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param load_artifact_hook: A callable that takes an Artifact and returns the value
    stored in the Artifact.
    :type load_artifact_hook: ArtifactLoadHook
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: None
    :rtype: None
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return await adelete_from_cluster_memory(
                key=key,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    return await adelete_artifact(
        name=key,
        namespace=namespace,
        **(artifact_params or {}),
    )


def list_objects(
    prefix: str | None = None,
    namespace: str | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> tuple[list[str], list[str]]:
    """
    List objects in the object store.

    This will list objects in cluster memory first, and if not found
    will fallback to listing Artifacts.

    :param prefix: The prefix to filter the objects by.
    :type prefix: str | None
    :param namespace: The namespace to list objects from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: A tuple containing the list of keys in cluster memory and the list of Artifact names.
    :rtype: tuple[list[str], list[str]]
    """
    return (
        list_cluster_memory(
            prefix=prefix,
            namespace=namespace,
            backend=executor,
            **(cluster_memory_params or {})
        ),
        list_artifacts(
            prefix=prefix,
            namespace=namespace,
            **(artifact_params or {})
        ),
    )


async def alist_objects(
    prefix: str | None = None,
    namespace: str | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> tuple[list[str], list[str]]:
    """
    List objects in the object store.

    This will list objects in cluster memory first, and if not found
    will fallback to listing Artifacts.

    :param prefix: The prefix to filter the objects by.
    :type prefix: str | None
    :param namespace: The namespace to list objects from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: A tuple containing the list of keys in cluster memory and the list of Artifact names.
    :rtype: tuple[list[str], list[str]]
    """
    return (
        await alist_cluster_memory(
            prefix=prefix,
            namespace=namespace,
            backend=executor,
            **(cluster_memory_params or {})
        ),
        await alist_artifacts(
            prefix=prefix,
            namespace=namespace,
            **(artifact_params or {})
        ),
    )


def exists_object(
    key: str,
    *,
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> bool:
    """
    Check if an object exists in the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to check for existence.
    :type key: str
    :param namespace: The namespace to check in, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: True if the object exists, False otherwise.
    :rtype: bool
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return exists_in_cluster_memory(
                key=key,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    try:
        get_artifact(
            name=key,
            namespace=namespace,
            create=False,
            **(artifact_params or {}),
        )
        return True
    except FileNotFoundError:
        return False


async def aexists_object(
    key: str,
    *,
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> bool:
    """
    Check if an object exists in the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to check for existence.
    :type key: str
    :param namespace: The namespace to check in, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to the configuration's
    default object store strategy.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :param artifact_params: Additional parameters to pass to the Artifact.
    :type artifact_params: dict | None
    :return: True if the object exists, False otherwise.
    :rtype: bool
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return await aexists_in_cluster_memory(
                key=key,
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    try:
        await aget_artifact(
            name=key,
            namespace=namespace,
            create=False,
            **(artifact_params or {}),
        )
        return True
    except FileNotFoundError:
        return False


def clear_objects(
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
) -> None:
    """
    Clear all objects in the object store.

    This will clear objects in cluster memory first, and if not found
    will fallback to clearing Artifacts.

    :param namespace: The namespace to clear objects from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to cluster memory.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :return: None
    :rtype: None
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return clear_cluster_memory(
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    clear_artifacts(
        namespace=namespace,
        **(cluster_memory_params or {})
    )

async def aclear_objects(
    namespace: str | None = None,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
) -> None:
    """
    Clear all objects in the object store.

    This will clear objects in cluster memory first, and if not found
    will fallback to clearing Artifacts.

    :param namespace: The namespace to clear objects from, defaults to the namespace
    of the current WorkflowRunContext.
    :type namespace: str | None
    :param strategy: The strategy to use for storing the object, defaults to cluster memory.
    :type strategy: Strategy | None
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :type executor: str | None
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :type cluster_memory_params: dict | None
    :return: None
    :rtype: None
    """
    if not strategy:
        strategy = Strategy(get_configuration().services.compute.default_os_strategy)  # type: ignore[union-attr]

    if strategy != Strategy.ARTIFACT:
        try:
            return await aclear_cluster_memory(
                namespace=namespace,
                backend=executor,
                **(cluster_memory_params or {})
            )
        except Exception:
            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    await aclear_artifacts(
        namespace=namespace,
        **(cluster_memory_params or {})
    )


# ---------------------------
# For backwards compatibility
# ---------------------------

def put(
    key: str,
    value: Any,
    *,
    namespace: str | None = None,
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    save_artifact_hook: ArtifactSaveHook = default_save_hook(),  # noqa: B008
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> None:
    logger.warning(
        "DeprecationWarning",
        message=(
            "The `put` function is deprecated and will be removed in a future version. "
            "Use `put_object` instead."
        ),
    )

    return put_object(
        key=key,
        value=value,
        namespace=namespace,
        artifact_only=artifact_only,
        strategy=strategy,
        executor=executor,
        save_artifact_hook=save_artifact_hook,
        cluster_memory_params=cluster_memory_params,
        artifact_params=artifact_params,
    )


def get(
    key: str,
    *,
    namespace: str | None = None,
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    load_artifact_hook: ArtifactLoadHook = default_load_hook(),  # noqa: B008
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> Any:
    logger.warning(
        "DeprecationWarning",
        message=(
            "The `get` function is deprecated and will be removed in a future version. "
            "Use `get_object` instead."
        ),
    )

    return get_object(
        key=key,
        namespace=namespace,
        artifact_only=artifact_only,
        strategy=strategy,
        executor=executor,
        load_artifact_hook=load_artifact_hook,
        cluster_memory_params=cluster_memory_params,
        artifact_params=artifact_params,
    )


def delete(
    key: str,
    *,
    namespace: str | None = None,
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict | None = None,
    artifact_params: dict | None = None,
) -> None:
    logger.warning(
        "DeprecationWarning",
        message=(
            "The `delete` function is deprecated and will be removed in a future version. "
            "Use `delete_object` instead."
        ),
    )

    return delete_object(
        key=key,
        namespace=namespace,
        artifact_only=artifact_only,
        strategy=strategy,
        executor=executor,
        cluster_memory_params=cluster_memory_params,
        artifact_params=artifact_params,
    )


put.__doc__ = put_object.__doc__
get.__doc__ = get_object.__doc__
delete.__doc__ = delete_object.__doc__
