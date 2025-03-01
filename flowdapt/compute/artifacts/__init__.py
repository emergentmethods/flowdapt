from flowdapt.compute.artifacts.interface import Artifact, ArtifactFile
from flowdapt.compute.resources.workflow.context import get_run_context
from flowdapt.lib.config import get_configuration


def _get_values_from_context(
    namespace: str = "", protocol: str = "", base_path: str = "", **params
) -> tuple[str, str, str, dict]:
    """
    Get default values from the current run context.
    """
    _app_config = get_configuration()
    _context = get_run_context()

    namespace = namespace or _context.namespace
    protocol = protocol or _app_config.storage.protocol
    base_path = base_path or _app_config.storage.base_path
    params = {**_app_config.storage.parameters, **params}

    return namespace, protocol, base_path, params


def get_artifact(
    name: str,
    namespace: str = "",
    protocol: str = "",
    base_path: str = "",
    *,
    create: bool = False,
    **params,
) -> Artifact:
    """
    Get an Artifact with the given name and namespace.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace, protocol=protocol, base_path=base_path, **params
    )

    try:
        return Artifact.get_artifact(
            name=name, namespace=namespace, protocol=protocol, base_path=base_path, **params
        )
    except FileNotFoundError:
        if create:
            return Artifact.new_artifact(
                name=name, namespace=namespace, protocol=protocol, base_path=base_path, **params
            )
        else:
            raise


def list_artifacts(
    namespace: str = "", protocol: str = "", base_path: str = "", **params
) -> list[Artifact]:
    """
    List all artifacts in the given namespace.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace, protocol=protocol, base_path=base_path, **params
    )

    return Artifact.list_artifacts(
        namespace=namespace, protocol=protocol, base_path=base_path, **params
    )


def new_artifact(
    name: str, namespace: str = "", protocol: str = "", base_path: str = "", **params
) -> Artifact:
    """
    Create a new Artifact with the given name and namespace.
    """
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace=namespace, protocol=protocol, base_path=base_path, **params
    )

    return Artifact.new_artifact(
        name=name, namespace=namespace, protocol=protocol, base_path=base_path, **params
    )


__all__ = (
    "Artifact",
    "ArtifactFile",
)
