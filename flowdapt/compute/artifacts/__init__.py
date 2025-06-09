from flowdapt.compute.artifacts.interface import Artifact, ArtifactFile
from flowdapt.compute.resources.workflow.context import get_run_context
from flowdapt.lib.config import get_configuration


def _get_values_from_context(
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> tuple[str, str, str, dict]:
    _app_config = get_configuration()
    _context = get_run_context()

    namespace = namespace or _context.namespace
    protocol = protocol or _app_config.storage.protocol
    base_path = base_path or _app_config.storage.base_path
    params = {**_app_config.storage.parameters, **params}

    return namespace, protocol, base_path, params


def get_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    *,
    create: bool = False,
    **params,
) -> Artifact:
    """
    Get an Artifact with the given name and namespace.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param create: If True, a new artifact will be created if it does not exist.
    :type create: bool
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: The Artifact object.
    :rtype: Artifact
    :raises FileNotFoundError: If the artifact does not exist and create is False.
    :raises ValueError: If the artifact name is not valid.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    try:
        return Artifact.get_artifact(
            name=name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params
        )
    except FileNotFoundError:
        if create:
            return Artifact.new_artifact(
                name=name,
                namespace=namespace,
                protocol=protocol,
                base_path=base_path,
                **params
            )
        else:
            raise


async def aget_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    *,
    create: bool = False,
    **params,
) -> Artifact:
    """
    Get an Artifact with the given name and namespace.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param create: If True, a new artifact will be created if it does not exist.
    :type create: bool
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: The Artifact object.
    :rtype: Artifact
    :raises FileNotFoundError: If the artifact does not exist and create is False.
    :raises ValueError: If the artifact name is not valid.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    try:
        return await Artifact.aget_artifact(
            name=name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params
        )
    except FileNotFoundError:
        if create:
            return await Artifact.anew_artifact(
                name=name,
                namespace=namespace,
                protocol=protocol,
                base_path=base_path,
                **params
            )
        else:
            raise


def list_artifacts(
    prefix: str | None = None,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> list[str]:
    """
    List all artifact names in the given namespace.

    :param prefix: The prefix to filter artifacts by. If None, all artifacts will
    be listed.
    :type prefix: str | None
    :param namespace: The namespace to list artifacts from. If None, the current
    run context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifacts. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifacts. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: A list of Artifact objects.
    :rtype: list[Artifact]
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    return Artifact.list_artifacts(
        prefix=prefix,
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )


async def alist_artifacts(
    prefix: str | None = None,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> list[str]:
    """
    List all artifact names in the given namespace.

    :param prefix: The prefix to filter artifacts by. If None, all artifacts will
    be listed.
    :type prefix: str | None
    :param namespace: The namespace to list artifacts from. If None, the current
    run context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifacts. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifacts. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: A list of Artifact objects.
    :rtype: list[Artifact]
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    return await Artifact.alist_artifacts(
        prefix=prefix,
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )


def new_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> Artifact:
    """
    Create a new Artifact with the given name and namespace.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: The newly created Artifact object.
    :rtype: Artifact
    :raises FileExistsError: If the artifact already exists.
    :raises AssertionError: If the artifact name is empty.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    return Artifact.new_artifact(
        name=name,
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )


async def anew_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> Artifact:
    """
    Create a new Artifact with the given name and namespace.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: The newly created Artifact object.
    :rtype: Artifact
    :raises FileExistsError: If the artifact already exists.
    :raises AssertionError: If the artifact name is empty.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    return await Artifact.anew_artifact(
        name=name,
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )


def delete_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> None:
    """
    Delete an Artifact with the given name and namespace.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    artifact = Artifact.get_artifact(
        name=name,
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )
    artifact.delete()


async def adelete_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> None:
    """
    Delete an Artifact with the given name and namespace.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    artifact = await Artifact.aget_artifact(
        name=name,
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )
    await artifact.adelete()


def exists_artifact(
    name: str,
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> bool:
    """
    Check if an Artifact with the given name and namespace exists.

    :param name: The name of the artifact.
    :type name: str
    :param namespace: The namespace of the artifact. If None, the current run
    context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifact. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifact. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    :return: True if the artifact exists, False otherwise.
    :rtype: bool
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    try:
        Artifact.get_artifact(
            name=name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params
        )
        return True
    except FileNotFoundError:
        return False


def clear_artifacts(
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> None:
    """
    Clear all artifacts in the given namespace.

    :param namespace: The namespace to clear artifacts from. If None, the current
    run context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifacts. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifacts. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    for artifact_name in Artifact.list_artifacts(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    ):
        artifact = get_artifact(
            name=artifact_name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params
        )
        artifact.delete()


async def aclear_artifacts(
    namespace: str | None = None,
    protocol: str | None = None,
    base_path: str | None = None,
    **params
) -> None:
    """
    Clear all artifacts in the given namespace.

    :param namespace: The namespace to clear artifacts from. If None, the current
    run context's namespace will be used.
    :type namespace: str | None
    :param protocol: The protocol to use for the artifacts. If None, the default
    protocol from the configuration will be used.
    :type protocol: str | None
    :param base_path: The base path for the artifacts. If None, the default base
    path from the configuration will be used.
    :type base_path: str | None
    :param params: Additional parameters to pass to the Artifact.
    :type params: dict
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    )

    for artifact_name in await Artifact.alist_artifacts(
        namespace=namespace,
        protocol=protocol,
        base_path=base_path,
        **params
    ):
        artifact = await aget_artifact(
            name=artifact_name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params
        )
        await artifact.adelete()



__all__ = (
    "Artifact",
    "ArtifactFile",
    "get_artifact",
    "aget_artifact",
    "list_artifacts",
    "alist_artifacts",
    "new_artifact",
    "anew_artifact",
    "delete_artifact",
    "adelete_artifact",
    "exists_artifact",
    "clear_artifacts",
    "aclear_artifacts",
)
