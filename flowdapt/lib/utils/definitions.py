from manifest import Manifest

from flowdapt.lib.plugins import Plugin
from flowdapt.lib.utils.model import BaseModel, ValidationError


KNOWN_DEFINITION_EXTS = [".yaml", ".yml", ".json"]


async def get_valid_definitions(plugins: list[Plugin], model: type[BaseModel]) -> list[Manifest]:
    """
    Get all valid definitions from a plugin manifest.
    """
    definitions: list[Manifest] = []
    definition_model = type("DefinitionModel", (Manifest, model), {})

    for plugin in plugins:
        plugin_files = [
            filename
            for filename in await plugin.list_datafiles()
            if any([ext in filename.name for ext in KNOWN_DEFINITION_EXTS])
        ]

        for file in plugin_files:
            try:
                definitions.append(await definition_model.from_file(file_path=file))
            except ValidationError:
                pass

    return definitions
