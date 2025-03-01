import socket
import sys
import tempfile
import zipfile
from pathlib import Path

from distributed import Client, Nanny, NannyPlugin
from distributed.diagnostics.plugin import Environ, PipInstall
from distributed.diagnostics.plugin import UploadDirectory as DaskUploadDirectory

from flowdapt.lib.logger import get_logger
from flowdapt.lib.plugins import Plugin
from flowdapt.lib.utils.asynctools import call_bash_command, run_in_thread
from flowdapt.lib.utils.misc import (
    compute_hash,
    get_site_packages_dir,
    in_path,
    recursive_rmdir,
)


logger = get_logger(__name__)

__all__ = (
    "UploadDirectory",
    "UploadPlugins",
    "Environ",
    "SetupPluginRequirements",
    "PipInstall",
)


def create_plugin_bundle(
    plugins: list[Plugin],
    skip_words: list[str] = [
        "__pycache__",
        ".pyc",
        ".git",
        ".github",
        ".pytest_cache",
        "tests",
        "docs",
    ],
) -> bytes:
    """
    Create a plugin bundle by zipping up the plugin modules and reading the data.

    :param plugins: List of Plugin objects.
    :param skip_words: List of words to skip when zipping up the plugin modules.
    :return: Bytes of the resulting zip file.
    """
    # Ensure we're dealing with packages and not simple modules
    # Note: Python packages can be split up into multiple directories but for now
    # we just get the first path.
    paths_to_zip = [Path(p.module.__path__[0]) for p in plugins if hasattr(p.module, "__path__")]
    site_packages = get_site_packages_dir()

    # Discover any dist-info directories
    for plugin in plugins:
        name, version = plugin.name.replace("-", "_"), plugin.metadata.version
        dist_info = site_packages / f"{name}-{version}.dist-info"

        if dist_info.exists():
            logger.debug("FoundDistInfo", dist_info=dist_info)
            paths_to_zip.append(dist_info)

    # Create archive and return the bytes
    tmp_path = Path(tempfile.mktemp(suffix=".zip"))

    with zipfile.ZipFile(tmp_path, "w") as zf:
        for path in paths_to_zip:
            for file in path.rglob("*"):
                if not in_path(file, skip_words) or ".dist-info" in file.name:
                    logger.debug("AddingFile", file=file)
                    zf.write(file, arcname=file.relative_to(path.parent).as_posix())

    bytes = tmp_path.read_bytes()
    tmp_path.unlink()

    return bytes


class UploadDirectory(DaskUploadDirectory):
    def _teardown(self, nanny: Nanny):
        # TODO: Refactor this method and UploadPlugins._teardown to a single method
        directory: Path = Path(nanny.local_directory) / self.path
        # Ensure the path is a directory before proceeding
        if not directory.is_dir() or not directory.exists():
            return

        logger.info("RemovingDirectory", directory=directory, nanny=nanny.name)
        recursive_rmdir(directory)

    async def teardown(self, nanny: Nanny):
        await run_in_thread(self._teardown, nanny)


class UploadPlugins(NannyPlugin):
    restart = False

    def __init__(self, plugins: list[Plugin]):
        """
        Initialize the plugin by zipping the Plugin modules and reading the data.
        """
        self._plugin_dirs = []
        self._hash = compute_hash(
            *(plugin.name for plugin in plugins), *(plugin.metadata.version for plugin in plugins)
        )
        self._data = create_plugin_bundle(plugins)

    def _setup(self, nanny):
        nanny_dir = Path(nanny.local_directory)
        upload_path: Path = nanny_dir / self._hash

        if not upload_path.exists():
            upload_path.write_bytes(self._data)

        site_packages = get_site_packages_dir()
        logger.info(
            "UploadingPlugins",
            nanny=nanny.name,
            file=upload_path,
        )

        with zipfile.ZipFile(upload_path) as z:
            for file in z.namelist():
                logger.info("ExtractingFile", file=file, nanny=nanny.name)
                z.extract(file, site_packages)

                extracted_path = site_packages / file

                if extracted_path.is_dir() and extracted_path.parent == site_packages:
                    self._plugin_dirs.append(extracted_path)

        upload_path.unlink()

    def _teardown(self, nanny: Nanny):
        if not self._plugin_dirs:
            return

        logger.info("RemovingPlugins", dirs=self._plugin_dirs, nanny=nanny.name)
        for dir in self._plugin_dirs:
            recursive_rmdir(dir)

    async def setup(self, nanny: Nanny):
        await run_in_thread(self._setup, nanny)

    async def teardown(self, nanny: Nanny):
        await run_in_thread(self._teardown, nanny)


class SetupPluginRequirements(NannyPlugin):
    """
    A Plugin for pip installing plugin requirements.
    """

    INSTALLER = "pip"
    restart = True

    def __init__(
        self,
        plugins: list[Plugin],
        pip_options: list[str] | None = None,
    ):
        self._plugins = {plugin.name: plugin.metadata.requirements for plugin in plugins}
        self._pip_options = pip_options or []
        self._client: Client

    async def setup(self, nanny: Nanny):
        from distributed.semaphore import Semaphore

        if not hasattr(self, "_client"):
            self._client = await Client(nanny.scheduler_addr, asynchronous=True)

        if await self._is_installed(nanny) or not self._plugins:
            await logger.ainfo(
                "PluginRequirementsExist",
                installer=self.INSTALLER,
                plugins=self.get_plugin_names(),
            )
            return

        async with await Semaphore(
            max_leases=1,
            name=socket.gethostname(),
            register=True,
            scheduler_rpc=nanny.scheduler,
            loop=nanny.loop,
        ):
            await logger.ainfo(
                "PluginRequirementsInstalling",
                installer=self.INSTALLER,
                plugins=self.get_plugin_names(),
            )

            await self.install(self.get_plugin_reqs())
            await self._set_installed(nanny, True)

    async def teardown(self, nanny: Nanny):
        if not await self._is_installed(nanny):
            return

        await logger.ainfo(
            "PluginsUninstalling", installer=self.INSTALLER, plugins=self.get_plugin_names()
        )

        await self.uninstall(self.get_plugin_reqs())
        await self._client.close()

    def get_plugin_names(self) -> list[str]:
        return list(self._plugins.keys())

    def get_plugin_reqs(self) -> list[str]:
        return [r for requirements in self._plugins.values() for r in requirements]

    async def uninstall(self, packages: list[str]) -> None:
        if not packages:
            return

        command = [sys.executable, "-m", "pip", "uninstall", "-y"] + packages

        await logger.ainfo("ExecutingBashCommand", command=command)
        await call_bash_command(command, stream_callbacks=[lambda x: print(x, end="", flush=True)])

    async def install(self, packages: list[str]) -> None:
        if not packages:
            return

        command = [sys.executable, "-m", "pip", "install"] + self._pip_options + packages

        await logger.ainfo("ExecutingBashCommand", command=command)
        await call_bash_command(command, stream_callbacks=[lambda x: print(x, end="", flush=True)])

    async def _is_installed(self, nanny: Nanny):
        return await self._client.get_metadata(self._compose_installed_key(nanny), default=False)

    async def _set_installed(self, nanny: Nanny, is_installed: bool = True):
        await self._client.set_metadata(
            self._compose_installed_key(nanny),
            is_installed,
        )

    def _compose_installed_key(self, nanny: Nanny):
        return [
            nanny.name,
            "installed",
            socket.gethostname(),
            compute_hash(*(self.get_plugin_reqs() + self.get_plugin_names())),
        ]
