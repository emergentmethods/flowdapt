from __future__ import annotations

from flowdapt.lib.domain.models import Resource
from flowdapt.lib.utils.model import (
    BaseModel,
    CallableOrImportString,
    field_validator,
)


WORKFLOW_RESOURCE_KIND = "workflow"


class WorkflowStage(BaseModel):
    type: str = "simple"  # Default to the simple stage type
    target: CallableOrImportString
    name: str
    description: str = ""
    version: str = ""
    depends_on: list[str] = []
    options: dict = {}
    resources: dict = {}
    priority: int | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value):
        from flowdapt.compute.resources.workflow.stage import get_available_stage_types

        if value not in get_available_stage_types():
            raise ValueError(f"Stage type `{value}` does not exist.")

        return value


class WorkflowSpec(BaseModel):
    stages: list[WorkflowStage]

    @field_validator("stages")
    @classmethod
    def stages_not_empty(cls, v):
        assert len(v) > 0
        return v


class WorkflowResource(Resource):
    kind: str = WORKFLOW_RESOURCE_KIND
    spec: WorkflowSpec
