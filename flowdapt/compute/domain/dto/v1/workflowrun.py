from datetime import datetime
from typing import Any
from uuid import UUID

from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.lib.utils.model import BaseModel, model_dump


class V1Alpha1WorkflowRunReadResponse(BaseModel):
    uid: UUID
    name: str
    workflow: str
    started_at: datetime
    finished_at: datetime | None
    result: Any | None
    state: str
    source: str | None

    @classmethod
    def from_model(cls, model: WorkflowRun):
        return cls(**model_dump(model))
