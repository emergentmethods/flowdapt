from importlib.metadata import EntryPoint, distribution, entry_points, version
from importlib.metadata import files as package_files
from pathlib import Path
from typing import Any

from flowdapt.lib.plugins.utils import parse_package_manifest
from flowdapt.lib.utils.asynctools import run_in_thread
from flowdapt.lib.utils.misc import in_path
from flowdapt.lib.utils.model import BaseModel, Field


_ENTRYPOINT_GROUP = "flowdapt.plugins"
PLUGIN_RESOURCE_KIND = "plugin"
DEFAULT_SKIP_WORDS = [
    "__pycache__",
    ".pyc",
    ".py",
    ".egg-info",
    ".dist-info",
    ".git",
    ".github",
    ".pytest_cache",
    "tests",
    "docs",
]


class PluginMetadata(BaseModel):
    description: str
    author: str
    license: str
    url: str
    version: str
    requirements: list[str] = []


class Plugin(BaseModel):
    name: str
    metadata: PluginMetadata
    module: Any = Field(..., exclude=True)

    @classmethod
    def from_entrypoint(cls, entrypoint: EntryPoint):
        dist = entrypoint.dist or distribution(entrypoint.module)

        return cls(
            name=dist.metadata["name"],
            metadata=PluginMetadata(
                description=dist.metadata.json.get("summary", ""),
                author=dist.metadata.json.get("author", ""),
                license=dist.metadata.json.get("license", ""),
                url=dist.metadata.json.get("url", ""),
                version=version(entrypoint.module),
                requirements=dist.metadata.json.get("requires_dist", []),
            ),
            module=entrypoint.load(),
        )

    async def list_datafiles(
        self,
        skip_words: list[str] = DEFAULT_SKIP_WORDS,
    ) -> list[Path]:
        """
        Get a list of datafiles bundled with the plugin.
        """
        files = package_files(self.name)
        data_files = []

        if files:
            for package_file_path in files:
                file_path = Path(package_file_path.locate())

                if in_path(file_path, skip_words) or await run_in_thread(file_path.is_dir):
                    continue

                if in_path(file_path, [".pth"]):
                    # If the file is a .pth file, we need to read the file
                    # and get the paths from it
                    paths = await run_in_thread(file_path.read_text)

                    for pathb in paths.splitlines():
                        if pathb:
                            pathb = str(pathb, "utf-8") if isinstance(pathb, bytes) else pathb
                            path = Path(pathb)
                            manifest_path = path / "MANIFEST.in"

                            if await run_in_thread(manifest_path.exists):
                                data_files.extend(
                                    await parse_package_manifest(
                                        manifest_path=manifest_path, skip_words=skip_words
                                    )
                                )

                    continue

                data_files.append(file_path)
        return data_files


class PluginManifest:
    root: dict[str, Plugin] = {}

    async def load_plugins(self):
        for entrypoint in list(entry_points(group=_ENTRYPOINT_GROUP)):
            plugin = Plugin.from_entrypoint(entrypoint)
            self.root[plugin.name] = plugin

    def get_plugin(self, name: str) -> Plugin:
        return self.root[name]

    def list_plugins(self) -> list[Plugin]:
        return list(self.root.values())

    def __len__(self):
        return len(self.root)
