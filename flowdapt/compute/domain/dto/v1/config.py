from enum import Enum

from flowdapt.lib.utils.model import BaseModel, model_dump
from flowdapt.lib.domain.dto.v1.base import V1Alpha1ResourceMetadata
from flowdapt.compute.domain.models.config import ConfigResource, CONFIG_RESOURCE_KIND


class V1Alpha1ConfigSelectorType(str, Enum):
    name = "name"
    annotation = "annotation"


class V1Alpha1ConfigSelector(BaseModel):
    kind: str | None = None
    type: V1Alpha1ConfigSelectorType = "name"
    value: str | dict[str, str] | None = None


class V1Alpha2ConfigSelector(V1Alpha1ConfigSelector):
    ...


class V1Alpha1ConfigResourceSpec(BaseModel):
    selector: V1Alpha1ConfigSelector | None = None
    data: dict

class V1Alpha2ConfigResourceSpec(BaseModel):
    selector: V1Alpha2ConfigSelector | None = None
    data: dict
    new: bool = False


class V1Alpha1ConfigResourceBase(BaseModel):
    kind: str = CONFIG_RESOURCE_KIND
    metadata: V1Alpha1ResourceMetadata
    spec: V1Alpha1ConfigResourceSpec


class V1Alpha2ConfigResourceBase(BaseModel):
    kind: str = CONFIG_RESOURCE_KIND
    metadata: V1Alpha1ResourceMetadata
    spec: V1Alpha2ConfigResourceSpec


class V1Alpha1ConfigResourceCreateRequest(V1Alpha1ConfigResourceBase):
    def to_model(self) -> ConfigResource:
        return ConfigResource(
            # Explicitly ignore internally populated fields
            **model_dump(self, exclude={"metadata": {"uid", "created_at", "updated_at"}}),
        )


class V1Alpha2ConfigResourceCreateRequest(V1Alpha2ConfigResourceBase):
    def to_model(self) -> ConfigResource:
        data = model_dump(
            self,
            exclude={
                "metadata": {"uid", "created_at", "updated_at"},
                "new": True
            }
        )
        return ConfigResource(**data)


class V1Alpha1ConfigResourceCreateResponse(V1Alpha1ConfigResourceBase):
    @classmethod
    def from_model(cls, model: ConfigResource):
        return cls(**model_dump(model))


class V1Alpha2ConfigResourceCreateResponse(V1Alpha2ConfigResourceBase):
    @classmethod
    def from_model(cls, model: ConfigResource):
        return cls(**{**model_dump(model), "new": True})


class V1Alpha1ConfigResourceUpdateRequest(V1Alpha1ConfigResourceBase):
    def to_model(self) -> ConfigResource:
        return ConfigResource(
            # Explicitly ignore internally populated fields
            **model_dump(self, exclude={"metadata": {"updated_at"}}),
        )


class V1Alpha1ConfigResourceUpdateResponse(V1Alpha1ConfigResourceBase):
    @classmethod
    def from_model(cls, model: ConfigResource):
        return cls(**model_dump(model))


class V1Alpha1ConfigResourceReadResponse(V1Alpha1ConfigResourceBase):
    @classmethod
    def from_model(cls, model: ConfigResource):
        return cls(**model_dump(model))
