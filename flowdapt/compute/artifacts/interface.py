from __future__ import annotations

import os
import re
from typing import Any, AsyncIterator, Iterator, Literal, overload

from asyncer import asyncify
from fsspec import AbstractFileSystem, filesystem

from flowdapt.lib.serializers import ORJSONSerializer


_ARTIFACT_METADATA_FILENAME = ".artifact.json"


def _validate_filename(filename: str) -> str:
    if not filename:
        raise ValueError("Filename cannot be empty.")
    if not re.match(r"^[A-Za-z0-9_\-\.]+$", filename):
        raise ValueError(
            "Artifact file `filename` can only contain alphanumeric characters,"
            f" underscores, hyphens, and dots. Got: `{filename}`"
        )

    return filename


class ArtifactFile:
    def __init__(
        self,
        filename: str,
        artifact: Artifact,
    ) -> None:
        self._filename = _validate_filename(filename)
        self._artifact = artifact
        self._path = f"{self._artifact.path}/{self._filename}"

    async def aload(self) -> None:
        """
        Load the artifact file from the filesystem.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        return await asyncify(self.load)()

    def load(self) -> None:
        """
        Load the artifact file from the filesystem.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        if not self._artifact.fs.exists(self._path):
            raise FileNotFoundError(f"Artifact file {self._path} does not exist.")

    @property
    def artifact(self):
        return self._artifact

    @property
    def name(self):
        return self._filename

    @property
    def path(self):
        return self._path

    def __repr__(self):
        return f"ArtifactFile<{self._path}>"

    @classmethod
    def exists(
        cls,
        artifact: Artifact,
        filename: str,
    ) -> bool:
        """
        Check if an artifact file exists.

        :param artifact: The artifact to check the file in.
        :type artifact: Artifact
        :param filename: The name of the file to check.
        :type filename: str
        :return: True if the file exists, False otherwise.
        :rtype: bool
        :raises ValueError: If the filename is invalid.
        """
        filename = _validate_filename(filename)
        return artifact.fs.exists(f"{artifact.path}/{filename}")

    @classmethod
    async def aexists(
        cls,
        artifact: Artifact,
        filename: str,
    ) -> bool:
        """
        Check if an artifact file exists.

        :param artifact: The artifact to check the file in.
        :type artifact: Artifact
        :param filename: The name of the file to check.
        :type filename: str
        :return: True if the file exists, False otherwise.
        :rtype: bool
        :raises ValueError: If the filename is invalid.
        """
        return await asyncify(cls.exists)(artifact=artifact, filename=filename)

    @classmethod
    def new(
        cls,
        artifact: Artifact,
        filename: str,
        content: Any = None,
    ) -> ArtifactFile:
        """
        Create a new artifact file.

        :param artifact: The artifact to create the file in.
        :type artifact: Artifact
        :param filename: The name of the file to create.
        :type filename: str
        :param content: The content of the file. If None, an empty file will be created.
        :type content: Any
        :return: An instance of ArtifactFile representing the new file.
        :rtype: ArtifactFile
        :raises FileExistsError: If the file already exists.
        """
        filename = _validate_filename(filename)
        path = f"{artifact.path}/{filename}"

        if artifact.fs.exists(path):
            raise FileExistsError(f"Artifact file {path} already exists.")

        if content is not None:
            with artifact.fs.open(
                path,
                mode=(
                    "w"
                    if isinstance(content, str)
                    else "wb"
                )
            ) as f:
                f.write(content)
        else:
            artifact.fs.touch(path)

        artifact_file = cls(filename, artifact)
        artifact_file.load()
        return artifact_file

    @classmethod
    async def anew(
        cls,
        artifact: Artifact,
        filename: str,
        content: Any = None,
    ) -> ArtifactFile:
        """
        Create a new artifact file.

        :param artifact: The artifact to create the file in.
        :type artifact: Artifact
        :param filename: The name of the file to create.
        :type filename: str
        :param content: The content of the file. If None, an empty file will be created.
        :type content: Any
        :return: An instance of ArtifactFile representing the new file.
        :rtype: ArtifactFile
        :raises FileExistsError: If the file already exists.
        """
        return await asyncify(cls.new)(
            artifact=artifact,
            filename=filename,
            content=content
        )

    def delete(self) -> None:
        """
        Delete the artifact file.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        self._artifact.fs.rm(self.path)

    async def adelete(self) -> None:
        """
        Delete the artifact file.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        await asyncify(self.delete)()

    @overload
    def read(self, size: int = -1, mode: Literal["r"] = "r") -> str:
        ...

    @overload
    def read(self, size: int = -1, mode: Literal["rb"] = "rb") -> bytes:
        ...

    def read(self, size: int = -1, mode: Literal["r","rb"] = "rb") -> str | bytes:
        """
        Read data from the artifact file.

        :param size: The number of bytes to read. If -1, reads the entire file.
        :type size: int
        :param mode: The mode to open the file in. Can be 'r' for text or 'rb' for binary.
        :type mode: str
        :return: The data read from the file, either as a string or bytes.
        :rtype: str | bytes
        :raises AssertionError: If the mode is not 'r' or 'rb'.
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        assert mode in ("r", "rb"), "Mode must be 'r' or 'rb'"
        with self._artifact.fs.open(self._path, mode=mode) as f:
            return f.read(size)

    @overload
    async def aread(self, size: int = -1, mode: Literal["r"] = "r") -> str:
        ...

    @overload
    async def aread(self, size: int = -1, mode: Literal["rb"] = "rb") -> bytes:
        ...

    async def aread(self, size: int = -1, mode: Literal["r", "rb"] = "rb") -> str | bytes:
        """
        Read data from the artifact file.

        :param size: The number of bytes to read. If -1, reads the entire file.
        :type size: int
        :param mode: The mode to open the file in. Can be 'r' for text or 'rb' for binary.
        :type mode: str
        :return: The data read from the file, either as a string or bytes.
        :rtype: str | bytes
        :raises AssertionError: If the mode is not 'r' or 'rb'.
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        assert mode in ("r", "rb"), "Mode must be 'r' or 'rb'"
        return await asyncify(self.read)(size=size, mode=mode)  # type: ignore[arg-type]

    def write(self, data: str | bytes) -> None:
        """
        Write data to the artifact file.

        :param data: The data to write to the file. Can be a string or bytes.
        :type data: str | bytes
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact file does not exist.
        """
        with self._artifact.fs.open(
            self._path,
            mode=(
                "w"
                if isinstance(data, str)
                else "wb"
            )
        ) as f:
            f.write(data)

    async def awrite(self, data: str | bytes) -> None:
        """
        Write data to the artifact file.

        :param data: The data to write to the file. Can be a string or bytes.
        :type data: str | bytes
        :return: None
        :rtype: None
        """
        await asyncify(self.write)(data=data)


class Artifact:
    def __init__(
        self,
        name: str,
        namespace: str | None = None,
        protocol: str = "file",
        base_path: str | None = None,
        params: dict[str, Any] | None = None,
        *,
        fs: AbstractFileSystem | None = None,
    ) -> None:
        if not re.match(r"^[A-Za-z0-9_\-]+$", name):
            raise ValueError(
                "Artifact `name` can only contain alphanumeric characters,"
                f" underscores, and hyphens. Got: `{name}`"
            )

        if fs and (protocol and params):
            raise ValueError("Cannot specify both `_fs` and `protocol`/`params`.")

        self._name = name
        self._namespace = namespace or "default"
        self._base_path = base_path or ""
        self._fs = fs or filesystem(
            protocol=protocol,
            **(params or {})
        )
        self._metadata: dict[str, Any] = {}

    @staticmethod
    def _get_full_path(base_path: str, namespace: str, name: str = "") -> str:
        return f"{base_path}/artifacts/{namespace}/{name}"

    def _read_metadata(self) -> None:
        meta_file = self.new_file(_ARTIFACT_METADATA_FILENAME, exist_ok=True)
        if (content := meta_file.read(mode="rb")):
            self._metadata = ORJSONSerializer.loads(content)

    async def _aread_metadata(self) -> None:
        return await asyncify(self._read_metadata)()

    def _write_metadata(self) -> None:
        meta_file = self.get_file(_ARTIFACT_METADATA_FILENAME, create=True)
        meta_file.write(ORJSONSerializer.dumps(self._metadata))

    async def _awrite_metadata(self) -> None:
        return await asyncify(self._write_metadata)()

    @property
    def fs(self) -> AbstractFileSystem:
        return self._fs

    @property
    def uri(self) -> str:
        return f"{self._fs.protocol}://{self.path}"

    @property
    def path(self) -> str:
        return Artifact._get_full_path(self._base_path, self._namespace, self._name)

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    async def _aensure_exists(self) -> None:
        return await asyncify(self._ensure_exists)()

    def _ensure_exists(self) -> None:
        if not self.exists():
            raise FileNotFoundError(
                f"No Artifact existing in namespace `{self.namespace}` with the path `{self.name}`"
            )

    async def aload(self) -> None:
        """
        Load the artifact from the filesystem.

        This method checks if the artifact exists and reads its metadata.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        await self._aensure_exists()
        await self._aread_metadata()

    def load(self) -> None:
        """
        Load the artifact from the filesystem.

        This method checks if the artifact exists and reads its metadata.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        self._ensure_exists()
        self._read_metadata()

    async def aexists(self) -> bool:
        """
        Check if the artifact exists.

        :return: True if the artifact exists, False otherwise.
        :rtype: bool
        :raises FileNotFoundError: If the artifact does not exist.
        """
        return await asyncify(self.exists)()

    def exists(self) -> bool:
        """
        Check if the artifact exists.

        :return: True if the artifact exists, False otherwise.
        :rtype: bool
        :raises FileNotFoundError: If the artifact does not exist.
        """
        return self.fs.exists(self.path)

    async def alist_files(self, include_meta: bool = False) -> list[ArtifactFile]:
        """
        List all files in the artifact.

        :param include_meta: If True, will include the metadata file in the list.
        :type include_meta: bool
        :return: A list of ArtifactFile instances representing the files in the artifact.
        :rtype: list[ArtifactFile]
        :raises FileNotFoundError: If the artifact does not exist.
        :raises ValueError: If the artifact path is invalid.
        """
        return await asyncify(self.list_files)(include_meta)

    def list_files(self, include_meta: bool = False) -> list[ArtifactFile]:
        """
        List all files in the artifact.

        :param include_meta: If True, will include the metadata file in the list.
        :type include_meta: bool
        :return: A list of ArtifactFile instances representing the files in the artifact.
        :rtype: list[ArtifactFile]
        :raises FileNotFoundError: If the artifact does not exist.
        :raises ValueError: If the artifact path is invalid.
        """
        self._ensure_exists()
        return [
            ArtifactFile(os.path.basename(filename), self)
            for filename in self.fs.ls(self.path, detail=False)
            if _ARTIFACT_METADATA_FILENAME not in filename or include_meta
        ]

    async def aget_file(self, filename: str, create: bool = False) -> ArtifactFile:
        """
        Get a file from the artifact.

        :param filename: The name of the file to get.
        :type filename: str
        :param create: If True, will create the file if it does not exist.
        :type create: bool
        :return: An instance of ArtifactFile representing the file.
        :rtype: ArtifactFile
        :raises FileNotFoundError: If the artifact does not exist or the file does not exist.
        :raises ValueError: If the filename is invalid.
        """
        await self._aensure_exists()
        try:
            artifact_file = ArtifactFile(filename, self)
            await artifact_file.aload()
            return artifact_file
        except FileNotFoundError:
            if create:
                return await self.anew_file(filename)
            else:
                raise

    def get_file(self, filename: str, create: bool = False) -> ArtifactFile:
        """
        Get a file from the artifact.

        :param filename: The name of the file to get.
        :type filename: str
        :param create: If True, will create the file if it does not exist.
        :type create: bool
        :return: An instance of ArtifactFile representing the file.
        :rtype: ArtifactFile
        :raises FileNotFoundError: If the artifact does not exist or the file does not exist.
        :raises ValueError: If the filename is invalid.
        """
        self._ensure_exists()
        try:
            artifact_file = ArtifactFile(filename, self)
            artifact_file.load()
            return artifact_file
        except FileNotFoundError:
            if create:
                return self.new_file(filename)
            else:
                raise

    async def anew_file(
        self,
        filename: str,
        content: Any = None,
        *,
        exist_ok: bool = True,
    ) -> ArtifactFile:
        """
        Create a new file in the artifact.

        :param filename: The name of the file to create.
        :type filename: str
        :param content: The content of the file. If None, an empty file will be created.
        :type content: Any
        :param exist_ok: If True, will return the existing file if it already exists.
        :type exist_ok: bool
        :return: An instance of ArtifactFile representing the new file.
        :rtype: ArtifactFile
        :raises FileExistsError: If the file already exists and `exist_ok` is False.
        :raises FileNotFoundError: If the artifact does not exist.
        :raises ValueError: If the filename is invalid.
        """
        await self._aensure_exists()

        try:
            return await ArtifactFile.anew(self, filename, content)
        except FileExistsError:
            if exist_ok:
                return await self.aget_file(filename)
            else:
                raise

    def new_file(
        self,
        filename: str,
        content: Any = None,
        *,
        exist_ok: bool = True,
    ) -> ArtifactFile:
        """
        Create a new file in the artifact.

        :param filename: The name of the file to create.
        :type filename: str
        :param content: The content of the file. If None, an empty file will be created.
        :type content: Any
        :param exist_ok: If True, will return the existing file if it already exists.
        :type exist_ok: bool
        :return: An instance of ArtifactFile representing the new file.
        :rtype: ArtifactFile
        :raises FileExistsError: If the file already exists and `exist_ok` is False.
        :raises FileNotFoundError: If the artifact does not exist.
        :raises ValueError: If the filename is invalid.
        """
        self._ensure_exists()

        try:
            return ArtifactFile.new(self, filename, content)
        except FileExistsError:
            if exist_ok:
                return self.get_file(filename)
            else:
                raise

    async def adelete_file(self, filename: str) -> None:
        """
        Delete a file from the artifact.

        :param filename: The name of the file to delete.
        :type filename: str
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist or the file does not exist.
        :raises ValueError: If the filename is invalid.
        """
        await self._aensure_exists()
        artifact_file = await self.aget_file(filename)
        await artifact_file.adelete()

    def delete_file(self, filename: str) -> None:
        """
        Delete a file from the artifact.

        :param filename: The name of the file to delete.
        :type filename: str
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist or the file does not exist.
        :raises ValueError: If the filename is invalid.
        """
        self._ensure_exists()
        artifact_file = self.get_file(filename)
        artifact_file.delete()

    async def ahas_file(self, filename: str) -> bool:
        """
        Check if the artifact has a file with the given filename.

        :param filename: The name of the file to check.
        :type filename: str
        :return: True if the file exists in the artifact, False otherwise.
        :rtype: bool
        :raises FileNotFoundError: If the artifact does not exist.
        :raises ValueError: If the filename is invalid.
        """
        await self._aensure_exists()
        return await ArtifactFile.aexists(self, filename)

    def has_file(self, filename: str) -> bool:
        """
        Check if the artifact has a file with the given filename.

        :param filename: The name of the file to check.
        :type filename: str
        :return: True if the file exists in the artifact, False otherwise.
        :rtype: bool
        :raises FileNotFoundError: If the artifact does not exist.
        :raises ValueError: If the filename is invalid.
        """
        self._ensure_exists()
        return ArtifactFile.exists(self, filename)

    async def adelete(self) -> None:
        """
        Delete the artifact and all its files.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        await asyncify(self.delete)()

    def delete(self) -> None:
        """
        Delete the artifact and all its files.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        self._ensure_exists()
        self.fs.rm(self.path, recursive=True)

    async def aclear(self) -> None:
        """
        Clear all files in the artifact. This will remove all files in the artifact
        but keep the artifact itself.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        await asyncify(self.clear)()

    def clear(self) -> None:
        """
        Clear all files in the artifact. This will remove all files in the artifact
        but keep the artifact itself.

        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        self._ensure_exists()

        for file in self.list_files():
            file.delete()

    def get_meta(self, key: str, /, default: Any = None) -> Any:
        """
        Get a metadata entry for the artifact.

        :param key: The key for the metadata entry.
        :type key: str
        :param default: The default value to return if the key does not exist.
        :type default: Any
        :return: The value of the metadata entry or the default value.
        :rtype: Any
        :raises FileNotFoundError: If the artifact does not exist.
        """
        self._ensure_exists()
        self._read_metadata()
        return self._metadata.get(key, default)

    async def aget_meta(self, key: str, /, default: Any = None) -> Any:
        """
        Get a metadata entry for the artifact.

        :param key: The key for the metadata entry.
        :type key: str
        :param default: The default value to return if the key does not exist.
        :type default: Any
        :return: The value of the metadata entry or the default value.
        :rtype: Any
        :raises FileNotFoundError: If the artifact does not exist.
        """
        return await asyncify(self.get_meta)(key, default)

    def set_meta(self, key: str, value: Any) -> None:
        """
        Set a metadata entry for the artifact.

        :param key: The key for the metadata entry.
        :type key: str
        :param value: The value for the metadata entry.
        :type value: Any
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        self._ensure_exists()
        self._read_metadata()
        self._metadata[key] = value
        self._write_metadata()

    async def aset_meta(self, key: str, value: Any) -> None:
        """
        Set a metadata entry for the artifact.

        :param key: The key for the metadata entry.
        :type key: str
        :param value: The value for the metadata entry.
        :type value: Any
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        await asyncify(self.set_meta)(key, value)

    def delete_meta(self, key: str) -> None:
        """
        Delete a metadata entry from the artifact.

        :param key: The key of the metadata entry to delete.
        :type key: str
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        self._ensure_exists()
        self._read_metadata()

        if key in self._metadata:
            del self._metadata[key]
            self._write_metadata()

    async def adelete_meta(self, key: str) -> None:
        """
        Delete a metadata entry from the artifact.

        :param key: The key of the metadata entry to delete.
        :type key: str
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the artifact does not exist.
        """
        await asyncify(self.delete_meta)(key)

    def __contains__(self, filename: str) -> bool:
        self._ensure_exists()
        return self.has_file(filename)

    def __iter__(self) -> Iterator[ArtifactFile]:
        self._ensure_exists()

        for file in self.list_files():
            yield file

    async def __aiter__(self) -> AsyncIterator[ArtifactFile]:
        await self._aensure_exists()

        for file in await self.alist_files():
            yield file

    def __getitem__(self, key: str) -> ArtifactFile:
        self._ensure_exists()
        return self.get_meta(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._ensure_exists()
        self.set_meta(key, value)

    def __delitem__(self, key: str) -> None:
        self._ensure_exists()
        self.delete_meta(key)

    def __repr__(self) -> str:
        return f"Artifact<{self.path}>"

    @classmethod
    def list_artifacts(
        cls,
        prefix: str | None = None,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str | None = None,
        **params,
    ) -> list[str]:
        """
        List all artifact names in the given namespace.

        :param prefix: Optional prefix to filter artifact names.
        :type prefix: str | None
        :param namespace: Namespace to list artifacts from, defaults to "default".
        :type namespace: str
        :param protocol: Protocol for the filesystem, defaults to "file".
        :type protocol: str
        :param base_path: Base path for the artifacts, defaults to None.
        :type base_path: str | None
        :param params: Additional parameters for the filesystem.
        :type params: dict
        :return: A list of Artifact names.
        :rtype: list[str]
        """
        fs: AbstractFileSystem = filesystem(protocol=protocol, **params)
        path = Artifact._get_full_path(base_path or "", namespace)
        if not fs.exists(path):
            return []

        return [
            name
            for filename in fs.ls(path, detail=False)
            if (
                isinstance(filename, str)
                and (name := os.path.basename(filename))
                and (not prefix or name.startswith(prefix))
            )
        ]

    @classmethod
    async def alist_artifacts(
        cls,
        prefix: str | None = None,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str | None = None,
        **params,
    ) -> list[str]:
        """
        List all artifact names in the given namespace.

        :param prefix: Optional prefix to filter artifact names.
        :type prefix: str | None
        :param namespace: Namespace to list artifacts from, defaults to "default".
        :type namespace: str
        :param protocol: Protocol for the filesystem, defaults to "file".
        :type protocol: str
        :param base_path: Base path for the artifacts, defaults to None.
        :type base_path: str | None
        :param params: Additional parameters for the filesystem.
        :type params: dict
        :return: A list of Artifact names.
        :rtype: list[str]
        """
        return await asyncify(cls.list_artifacts)(
            prefix=prefix,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params,
        )

    @classmethod
    def new_artifact(
        cls,
        name: str,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str | None = None,
        **params,
    ) -> Artifact:
        """
        Create a new artifact with the given name and namespace.

        :param name: Name of the artifact.
        :type name: str
        :param namespace: Namespace of the artifact, defaults to "default".
        :type namespace: str
        :param protocol: Protocol for the filesystem, defaults to "file".
        :type protocol: str
        :param base_path: Base path for the artifact, defaults to None.
        :type base_path: str | None
        :param params: Additional parameters for the filesystem.
        :type params: dict
        :return: An instance of Artifact.
        :rtype: Artifact
        :raises FileExistsError: If the artifact already exists.
        :raises AssertionError: If the artifact name is empty.
        """
        assert name, "Artifact name cannot be empty"

        fs: AbstractFileSystem = filesystem(protocol=protocol, **params)
        path = Artifact._get_full_path(base_path or "", namespace, name)

        if not fs.exists(path):
            if "s3" in fs.protocol:
                fs.touch(f"{path}/{_ARTIFACT_METADATA_FILENAME}")
            else:
                fs.mkdir(path, create_parents=True)
        else:
            raise FileExistsError(
                f"Artifact with name `{name}` already exists in namespace `{namespace}`."
            )

        artifact = cls(
            name=name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            fs=fs,
        )
        artifact.load()
        return artifact

    @classmethod
    async def anew_artifact(
        cls,
        name: str,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str | None = None,
        **params,
    ) -> Artifact:
        """
        Create a new artifact with the given name and namespace.

        :param name: Name of the artifact.
        :type name: str
        :param namespace: Namespace of the artifact, defaults to "default".
        :type namespace: str
        :param protocol: Protocol for the filesystem, defaults to "file".
        :type protocol: str
        :param base_path: Base path for the artifact, defaults to None.
        :type base_path: str | None
        :param params: Additional parameters for the filesystem.
        :type params: dict
        :return: An instance of Artifact.
        :rtype: Artifact
        :raises FileExistsError: If the artifact already exists.
        :raises AssertionError: If the artifact name is empty.
        """
        return await asyncify(cls.new_artifact)(
            name=name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params,
        )

    @classmethod
    def get_artifact(
        cls,
        name: str,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str | None = None,
        **params,
    ) -> Artifact:
        """
        Get an existing artifact by its name and namespace.

        :param name: Name of the artifact.
        :type name: str
        :param namespace: Namespace of the artifact, defaults to "default".
        :type namespace: str
        :param protocol: Protocol for the filesystem, defaults to "file".
        :type protocol: str
        :param base_path: Base path for the artifact, defaults to None.
        :type base_path: str | None
        :param params: Additional parameters for the filesystem.
        :type params: dict
        :return: An instance of Artifact.
        :rtype: Artifact
        :raises FileNotFoundError: If the artifact does not exist.
        :raises AssertionError: If the artifact name is empty.
        """
        assert name, "Artifact name cannot be empty"

        fs: AbstractFileSystem = filesystem(protocol=protocol, **(params or {}))
        artifact = cls(
            name=name,
            namespace=namespace,
            base_path=base_path,
            fs=fs,
        )
        artifact.load()
        return artifact

    @classmethod
    async def aget_artifact(
        cls,
        name: str,
        namespace: str = "default",
        protocol: str = "file",
        base_path: str | None = None,
        **params,
    ) -> Artifact:
        """
        Get an existing artifact by its name and namespace.

        :param name: Name of the artifact.
        :type name: str
        :param namespace: Namespace of the artifact, defaults to "default".
        :type namespace: str
        :param protocol: Protocol for the filesystem, defaults to "file".
        :type protocol: str
        :param base_path: Base path for the artifact, defaults to None.
        :type base_path: str | None
        :param params: Additional parameters for the filesystem.
        :type params: dict
        :return: An instance of Artifact.
        :rtype: Artifact
        :raises FileNotFoundError: If the artifact does not exist.
        :raises AssertionError: If the artifact name is empty.
        """
        return await asyncify(cls.get_artifact)(
            name=name,
            namespace=namespace,
            protocol=protocol,
            base_path=base_path,
            **params,
        )
