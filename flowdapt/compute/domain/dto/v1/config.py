from enum import Enum

from flowdapt.compute.domain.models.config import CONFIG_RESOURCE_KIND, ConfigResource
from flowdapt.lib.domain.dto.v1.base import V1Alpha1ResourceMetadata
from flowdapt.lib.utils.model import BaseModel, model_dump


class V1Alpha1ConfigSelectorType(str, Enum):
    name = "name"
    annotation = "annotation"


class V1Alpha1ConfigSelector(BaseModel):
    kind: str | None = None
    type: V1Alpha1ConfigSelectorType = "name"
    value: str | dict[str, str] | None = None


class V1Alpha1ConfigResourceSpec(BaseModel):
    selector: V1Alpha1ConfigSelector | None = None
    data: dict


class V1Alpha1ConfigResourceBase(BaseModel):
    kind: str = CONFIG_RESOURCE_KIND
    metadata: V1Alpha1ResourceMetadata
    spec: V1Alpha1ConfigResourceSpec


class V1Alpha1ConfigResourceCreateRequest(V1Alpha1ConfigResourceBase):
    def to_model(self) -> ConfigResource:
        return ConfigResource(
            # Explicitly ignore internally populated fields
            **model_dump(self, exclude={"metadata": {"uid", "created_at", "updated_at"}}),
        )


class V1Alpha1ConfigResourceCreateResponse(V1Alpha1ConfigResourceBase):
    @classmethod
    def from_model(cls, model: ConfigResource):
        return cls(**model_dump(model))


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
