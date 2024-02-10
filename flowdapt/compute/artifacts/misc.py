from typing import Any

from flowdapt.compute.artifacts.interface import Artifact
from flowdapt.lib.serializers import CloudPickleSerializer, JSONSerializer


def json_to_artifact(name: str = "file"):
    """
    Persist a JSON object to an artifact.

    :param name: The name of the file to persist the JSON object to.
    """
    def _(artifact: Artifact, value: Any):
        artifact["value_type"] = "json"
        with artifact.new_file(f"{name}.json").open("wb") as file:
            file.write(JSONSerializer.dumps(value))
    return _


def json_from_artifact(name: str = "file"):
    """
    Load a JSON object from an artifact.

    :param name: The name of the file to load the JSON object from.
    """
    def _(artifact: Artifact):
        assert artifact["value_type"] == "json", "Artifact is not a JSON object."
        with artifact.get_file(f"{name}.json").open("rb") as file:
            return JSONSerializer.loads(file.read())
    return _


def pickle_to_artifact(name: str = "file"):
    """
    Persist a pickle object to an artifact.

    :param name: The name of the file to persist the pickle object to.
    """
    def _(artifact: Artifact, value: Any):
        artifact["value_type"] = "pickle"
        with artifact.new_file(f"{name}.pkl").open("wb") as file:
            file.write(CloudPickleSerializer.dumps(value))
    return _


def pickle_from_artifact(name: str = "file"):
    """
    Load a pickle object from an artifact.

    :param name: The name of the file to load the pickle object from.
    """
    def _(artifact: Artifact):
        assert artifact["value_type"] == "pickle", "Artifact is not a pickle object."
        with artifact.get_file(f"{name}.pkl").open("rb") as file:
            return CloudPickleSerializer.loads(file.read())
    return _
