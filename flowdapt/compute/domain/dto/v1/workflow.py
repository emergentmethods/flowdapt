from flowdapt.compute.domain.models.workflow import WORKFLOW_RESOURCE_KIND, WorkflowResource
from flowdapt.lib.domain.dto.v1.base import V1Alpha1ResourceMetadata
from flowdapt.lib.utils.model import BaseModel, model_dump


class V1Alpha1WorkflowStage(BaseModel):
    type: str = "simple"  # Default to the simple stage type
    target: str
    name: str
    description: str = ""
    version: str = ""
    depends_on: list[str] = []
    options: dict = {}
    resources: dict = {}
    priority: int | None = None


class V1Alpha1WorkflowResourceSpec(BaseModel):
    stages: list[V1Alpha1WorkflowStage]


class V1Alpha1WorkflowResourceBase(BaseModel):
    kind: str = WORKFLOW_RESOURCE_KIND
    metadata: V1Alpha1ResourceMetadata
    spec: V1Alpha1WorkflowResourceSpec


class V1Alpha1WorkflowResourceCreateRequest(V1Alpha1WorkflowResourceBase):
    def to_model(self) -> WorkflowResource:
        return WorkflowResource(
            **model_dump(self, exclude={"metadata": {"uid", "created_at", "updated_at"}}),
        )


class V1Alpha1WorkflowResourceCreateResponse(V1Alpha1WorkflowResourceBase):
    @classmethod
    def from_model(cls, model: WorkflowResource):
        return cls(**model_dump(model))


class V1Alpha1WorkflowResourceUpdateRequest(V1Alpha1WorkflowResourceBase):
    def to_model(self) -> WorkflowResource:
        return WorkflowResource(
            **model_dump(self, exclude={"metadata": {"updated_at"}}),
        )


class V1Alpha1WorkflowResourceUpdateResponse(V1Alpha1WorkflowResourceBase):
    @classmethod
    def from_model(cls, model: WorkflowResource):
        return cls(**model_dump(model))


class V1Alpha1WorkflowResourceReadResponse(V1Alpha1WorkflowResourceBase):
    @classmethod
    def from_model(cls, model: WorkflowResource):
        return cls(**model_dump(model))
