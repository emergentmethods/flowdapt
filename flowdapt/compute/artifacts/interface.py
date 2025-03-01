from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Any, Iterator

from fsspec import AbstractFileSystem, filesystem

from flowdapt.lib.serializers import ORJSONSerializer


_ARTIFACT_METADATA_FILENAME = ".artifact.json"


class ArtifactFile:
    def __init__(
        self,
        filename: str,
        artifact: Artifact,
    ):
        self._filename: str = filename
        self._artifact: Artifact = artifact

        self._path: str = f"{self._artifact.path}/{self._filename}"

        if not self._artifact._fs.exists(self._path):
            raise FileNotFoundError(f"No file existing with the path `{self._path}`")

    @classmethod
    def new(cls, artifact: Artifact, filename: str, content: Any = None) -> ArtifactFile:
        """
        Create a new ArtifactFile in the Artifact.

        :param artifact: The Artifact to create the file in.
        :param filename: The filename of the ArtifactFile.
        :param content: The content to write to the file.
        :return: The new ArtifactFile.
        """
        path = f"{artifact.path}/{filename}"

        if artifact._fs.exists(path):
            raise FileExistsError(f"File already exists with the path `{path}`")

        if content is not None:
            mode = "w" if isinstance(content, str) else "wb"
            with artifact._fs.open(path, mode) as f:
                f.write(content)
        else:
            artifact._fs.touch(path)

        return cls(filename, artifact)

    def __repr__(self):
        return f"ArtifactFile<{self._path}>"

    @property
    def artifact(self):
        return self._artifact

    @property
    def name(self):
        return self._filename

    @property
    def path(self):
        return self._path

    @contextmanager
    def open(self, mode: str = "r"):
        """
        Open the ArtifactFile in a context manager.
        """
        with self._artifact._fs.open(self._path, mode=mode) as f:
            yield f

    def remove(self):
        """
        Remove and delete the ArtifactFile from the Artifact.
        """
        self._artifact._fs.rm(self._path)

    def read(self, size: int = -1, mode: str = "rb"):
        """
        Read the ArtifactFile.
        """
        with self.open(mode=mode) as f:
            return f.read(size)

    def write(self, data: str | bytes):
        """
        Write to the ArtifactFile.
        """
        mode = "w" if isinstance(data, str) else "wb"

        with self.open(mode=mode) as f:
            f.write(data)


class Artifact:
    def __init__(
        self,
        name: str,
        namespace: str = "",
        protocol: str = "file",
        base_path: str = "",
        params: dict = {},
        *,
        _fs: AbstractFileSystem | None = None,
    ):
        if not re.match(r"^[A-Za-z0-9_\-]+$", name):
            raise ValueError(
                "Artifact `name` can only contain alphanumeric characters,"
                f" underscores, and hyphens. Got: `{name}`"
            )

        if _fs and protocol and params:
            raise ValueError("Cannot specify both `_fs` and `protocol`/`params`.")

        self._name: str = name
        self._namespace: str = namespace or "default"
        self._base_path: str = base_path
        self._fs: AbstractFileSystem = _fs or filesystem(protocol, **params)

        self._metadata: dict = {}

        if not self._check_path_exists(self._fs, self.path):
            raise FileNotFoundError(
                f"No Artifact existing in namespace `{self.namespace}` with the path `{self.name}`"
            )

        self._read_metadata()

    @classmethod
    def list_artifacts(
        cls, namespace: str, protocol: str = "file", base_path: str = "", **params
    ) -> list[Artifact]:
        """
        List all artifacts in the given namespace.

        :param namespace: The namespace to list artifacts in.
        :param protocol: The protocol to use for the artifacts.
        :param base_path: The base path to use for the artifacts.
        :param params: The parameters to pass to the filesystem.

        :return: A list of artifacts.
        """
        fs: AbstractFileSystem = filesystem(protocol, **params)
        path = cls._get_full_path(base_path, namespace)

        if not cls._check_path_exists(fs, path):
            return []

        artifacts = fs.ls(path, detail=False)
        return [
            cls(name=name.rsplit("/", 1)[-1], namespace=namespace, base_path=base_path, _fs=fs)
            for name in artifacts
        ]

    @classmethod
    def new_artifact(
        cls,
        name: str,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str = "",
        **params,
    ) -> Artifact:
        """
        Create a new artifact in the given namespace.

        :param name: The name of the artifact.
        :param namespace: The namespace to create the artifact in.
        :param protocol: The protocol to use for the artifact.
        :param base_path: The base path to use for the artifact.
        :param params: The parameters to pass to the filesystem.

        :return: The new artifact path
        """
        assert name, "Artifact `name` cannot be empty"

        fs: AbstractFileSystem = filesystem(protocol, **params)
        path = cls._get_full_path(base_path, namespace, name)

        if not cls._check_path_exists(fs, path):
            if "s3" in fs.protocol:
                # S3 doesn't actually create the bucket until we write a file to it
                fs.touch(f"{path}/{_ARTIFACT_METADATA_FILENAME}")
            else:
                fs.mkdir(path, create_parents=True)
        else:
            raise FileExistsError(f"Artifact `{name}` already exists in namespace `{namespace}`")

        return cls(name=name, namespace=namespace, base_path=base_path, _fs=fs)

    @classmethod
    def get_artifact(
        cls, name: str, namespace: str = "", protocol: str = "file", base_path: str = "", **params
    ) -> Artifact:
        """
        Get an existing artifact in the given namespace.

        :param name: The name of the artifact.
        :param namespace: The namespace to get the artifact from.
        :param protocol: The protocol to use for the artifact.
        :param base_path: The base path to use for the artifact.
        :param params: The parameters to pass to the filesystem.

        :return: The artifact.
        """
        return cls(
            name=name, namespace=namespace, protocol=protocol, base_path=base_path, params=params
        )

    @property
    def uri(self) -> str:
        return f"{self._fs.protocol}://{self.path}"

    @property
    def path(self) -> str:
        return Artifact._get_full_path(self._base_path, self._namespace, self._name)

    @property
    def exists(self) -> bool:
        return Artifact._check_path_exists(self._fs, self.path)

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def is_empty(self) -> bool:
        if not self.exists:
            return True
        return len(self.list_files()) < 1

    @property
    def metadata(self):
        return self._metadata

    def __repr__(self) -> str:
        return f"Artifact<{self.uri}>"

    def __bool__(self) -> bool:
        return not self.is_empty

    def __contains__(self, filename: str) -> bool:
        return self.has_file(filename)

    def __iter__(self) -> Iterator[ArtifactFile]:
        for file in self.list_files():
            yield file

    def __getitem__(self, key: str):
        return self.get_meta(key)

    def __setitem__(self, key: str, value: Any):
        self.set_meta(key, value)

    def __delitem__(self, key: str):
        del self._metadata[key]
        self._persist_metadata()

    def get_meta(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.

        :param key: The key to get.
        :param default: The default value to return if the key does not exist.

        :return: The value.
        """
        # TODO: Add some type of caching here
        self._read_metadata()

        try:
            return self._metadata[key]
        except KeyError:
            return default

    def set_meta(self, key: str, value: Any):
        """
        Set a metadata value.

        :param key: The key to set.
        :param value: The value to set.
        """
        self._metadata[key] = value
        self._persist_metadata()

    def del_meta(self, key: str):
        """
        Delete a metadata value.

        :param key: The key to delete.
        """
        del self._metadata[key]
        self._persist_metadata()

    def _read_metadata(self):
        if _ARTIFACT_METADATA_FILENAME in self:
            meta_file = self.get_file(_ARTIFACT_METADATA_FILENAME)
        else:
            # Create empty metadata file with empty JSON object
            meta_file = self.new_file(_ARTIFACT_METADATA_FILENAME, "{}")

        contents = meta_file.read()
        if contents:
            self._metadata = ORJSONSerializer.loads(contents)
        else:
            self._metadata = {}

    def _persist_metadata(self):
        meta_file = self.get_file(_ARTIFACT_METADATA_FILENAME, create=True)
        meta_file.write(ORJSONSerializer.dumps(self._metadata))

    @staticmethod
    def _get_full_path(base_path: str, namespace: str, name: str = ""):
        return f"{base_path}/artifacts/{namespace}/{name}"

    def _ensure_exists(self):
        if not self.exists:
            raise FileNotFoundError(f"No Artifact existing with the path `{self.path}`")

    @staticmethod
    def _check_path_exists(filesystem: AbstractFileSystem, path: str):
        return filesystem.exists(path)

    def list_files(self, include_meta: bool = False) -> list[ArtifactFile]:
        """
        Get a list of files in the Artifact.
        """
        self._ensure_exists()

        return [
            ArtifactFile(os.path.basename(filename), self)
            for filename in self._fs.ls(self.path, detail=False)
            if _ARTIFACT_METADATA_FILENAME not in filename and not include_meta
        ]

    def get_file(self, filename: str, create: bool = False) -> ArtifactFile:
        """
        Get a file in the Artifact.

        :param filename: The name of the file to get.
        :param create: Whether to create the file if it doesn't exist.
        :return: The ArtifactFile.
        """
        self._ensure_exists()

        try:
            return ArtifactFile(filename, self)
        except FileNotFoundError:
            if create:
                return self.new_file(filename)
            else:
                raise

    def new_file(
        self, filename: str, content: Any = None, *, exist_ok: bool = True
    ) -> ArtifactFile:
        """
        Create a new file in the Artifact.

        :param filename: The name of the file to create.
        :param content: The content of the file.
        :param exist_ok: Whether to throw an error if it already exists.
        :return: The ArtifactFile.
        """
        self._ensure_exists()

        try:
            return ArtifactFile.new(self, filename, content)
        except FileExistsError:
            if exist_ok:
                return self.get_file(filename)
            else:
                raise

    def delete_file(self, filename: str) -> None:
        """
        Delete a file in the Artifact.

        :param filename: The name of the file to delete.
        """
        self._ensure_exists()

        file = self.get_file(filename)
        file.remove()

    def has_file(self, filename: str) -> bool:
        """
        Check if a file exists in the Artifact.

        :param filename: The name of the file to check.
        """
        self._ensure_exists()

        return self._fs.exists(f"{self.path}/{filename}")

    def delete(self):
        """
        Delete the Artifact.
        """
        self._ensure_exists()
        self._fs.rm(self.path, recursive=True)

    def clear(self):
        """
        Clear the Artifact.
        """
        self._ensure_exists()

        for file in self.list_files():
            file.remove()

        self._metadata = {}

    @contextmanager
    def transaction(self):
        """
        Create a transaction context manager to defer file operations
        until the end of the context.
        """
        self._ensure_exists()

        with self._fs.transaction:
            yield self
