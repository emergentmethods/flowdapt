from enum import Enum
from typing import Any, Callable, Type

from flowdapt.compute.artifacts import Artifact, get_artifact
from flowdapt.compute.cluster_memory import (
    delete_from_cluster_memory,
    get_from_cluster_memory,
    put_in_cluster_memory,
)
from flowdapt.lib.config import get_configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.serializers import CloudPickleSerializer, Serializer


logger = get_logger(__name__)


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


def default_save_hook(serializer: Type[Serializer] | Serializer = CloudPickleSerializer):
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


def default_load_hook(serializer: type[Serializer] | Serializer = CloudPickleSerializer):
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

        return serializer.loads(obj_file.read())

    return _inner


def put(
    key: str,
    value: Any,
    *,
    namespace: str = "",
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    save_artifact_hook: Callable[[Artifact, Any], Any] = default_save_hook(),
    cluster_memory_params: dict = {},
    artifact_params: dict = {},
) -> None:
    """
    Put an object into the object store.

    This will attempt to put the object into cluster memory first, and if that fails
    will fallback to storing the object in an Artifact with the given key.

    :param key: The key to store the object under.
    :param value: The object to store.
    :param namespace: The namespace to store the object under, defaults to the namespace
    of the current WorkflowRunContext.
    :param artifact_only: If True, the strategy will be set to Artifact. *Deprecated* Use
    the `strategy` parameter instead.
    :param strategy: The strategy to use for storing the object, defaults to the Fallback strategy.
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :param save_artifact_hook: A callable that takes an Artifact and a value and saves
    the value to the Artifact.
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :param artifact_params: Additional parameters to pass to the Artifact.
    """
    if not strategy:
        strategy = get_configuration().services.compute.default_os_strategy

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
                key=key, value=value, namespace=namespace, backend=executor, **cluster_memory_params
            )
        except Exception as e:
            if not isinstance(e, KeyError):
                logger.debug("ClusterMemoryObjectPutFailed", key=key, error=str(e))

            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = get_artifact(name=key, namespace=namespace, create=True, **artifact_params)
    save_artifact_hook(_artifact, value)
    return


def get(
    key: str,
    *,
    namespace: str = "",
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    load_artifact_hook: Callable[[Artifact], Any] = default_load_hook(),
    cluster_memory_params: dict = {},
    artifact_params: dict = {},
) -> Any:
    """
    Get an object from the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to get the object from.
    :param namespace: The namespace to get the object from, defaults to the namespace
    of the current WorkflowRunContext.
    :param artifact_only: If True, the strategy will be set to Artifact. *Deprecated* Use
    the `strategy` parameter instead.
    :param strategy: The strategy to use for storing the object, defaults to the Fallback strategy.
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :param load_artifact_hook: A callable that takes an Artifact and returns the value
    stored in the Artifact.
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :param artifact_params: Additional parameters to pass to the Artifact.
    """
    if not strategy:
        strategy = get_configuration().services.compute.default_os_strategy

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
                key=key, namespace=namespace, backend=executor, **cluster_memory_params
            )
        except Exception as e:
            if not isinstance(e, KeyError):
                logger.debug("ClusterMemoryObjectGetFailed", key=key, error=str(e))

            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = get_artifact(name=key, namespace=namespace, **artifact_params)
    return load_artifact_hook(_artifact)


def delete(
    key: str,
    *,
    namespace: str = "",
    artifact_only: bool = False,
    strategy: Strategy | None = None,
    executor: str | None = None,
    cluster_memory_params: dict = {},
    artifact_params: dict = {},
) -> Any:
    """
    Delete an object from the object store.

    This will search for the object in cluster memory first, and if not found
    will fallback to searching for an Artifact with the given key.

    :param key: The key to get the object from.
    :param namespace: The namespace to get the object from, defaults to the namespace
    of the current WorkflowRunContext.
    :param artifact_only: If True, the strategy will be set to Artifact. *Deprecated* Use
    the `strategy` parameter instead.
    :param strategy: The strategy to use for storing the object, defaults to the Fallback strategy.
    :param executor: The executor kind for cluster memory, defaults to the executor of
    the current WorkflowRunContext.
    :param load_artifact_hook: A callable that takes an Artifact and returns the value
    stored in the Artifact.
    :param cluster_memory_params: Additional parameters to pass to the cluster memory backend.
    :param artifact_params: Additional parameters to pass to the Artifact.
    """
    if not strategy:
        strategy = get_configuration().services.compute.default_os_strategy

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
                key=key, namespace=namespace, backend=executor, **cluster_memory_params
            )
        except Exception as e:
            if not isinstance(e, KeyError):
                logger.debug("ClusterMemoryObjectDeleteFailed", key=key, error=str(e))

            if strategy == Strategy.CLUSTER_MEMORY:
                raise

    _artifact = get_artifact(name=key, namespace=namespace, create=True, **artifact_params)
    _artifact.delete()
