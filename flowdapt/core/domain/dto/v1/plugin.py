from flowdapt.lib.plugins import Plugin
from flowdapt.lib.utils.model import BaseModel, model_dump


class V1Alpha1PluginMetadata(BaseModel):
    description: str
    author: str
    license: str
    url: str
    version: str
    requirements: list[str] = []


class V1Alpha1Plugin(BaseModel):
    name: str
    metadata: V1Alpha1PluginMetadata
    module: str

    @classmethod
    def from_model(cls, model: Plugin):
        return cls(**{**model_dump(model), "module": model.module.__name__})


class V1Alpha1PluginFiles(BaseModel):
    files: list[str]

    @classmethod
    def from_model(cls, model: list[str]):
        return cls(files=model)
