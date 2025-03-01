from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, Any, TypeVar
from uuid import UUID, uuid4

from flowdapt.lib.database.annotations import Immutable
from flowdapt.lib.database.base import BaseStorage, Document, Field
from flowdapt.lib.utils.misc import generate_name
from flowdapt.lib.utils.mixins.active_record import ActiveRecordMixin
from flowdapt.lib.utils.model import (
    Field as PydanticField,
)


T = TypeVar("T")


class WorkflowRunState(str, Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    failed = "failed"


TERMINAL_STATES = [WorkflowRunState.finished, WorkflowRunState.failed]
WORKFLOW_RUN_RESOURCE_KIND = "workflow_run"


class WorkflowRun(Document, ActiveRecordMixin):
    uid: Annotated[UUID, Immutable] = PydanticField(default_factory=uuid4)
    name: Annotated[str, Immutable] = PydanticField(
        default_factory=lambda: f"{generate_name()}-{uuid4().hex[:8]}"
    )
    workflow: Annotated[str, Immutable]
    source: Annotated[str | None, Immutable] = None
    started_at: Annotated[datetime, Immutable] = PydanticField(default_factory=datetime.utcnow)
    finished_at: Annotated[datetime | None, Immutable] = None
    result: Annotated[Any | None, Immutable] = None
    state: str = WorkflowRunState.pending

    @classmethod
    async def _get(cls: type[T], database: BaseStorage, identifier: str | UUID) -> T | None:
        if isinstance(identifier, str):
            try:
                identifier = UUID(identifier)
            except ValueError:
                pass

        return await database.find_one(
            cls,
            (Field.uid == identifier) | (Field.name == identifier),
        )

    @classmethod
    async def get_most_recent(
        cls, database: BaseStorage, workflow_name: str, n_rows: int = 1
    ) -> list[WorkflowRun]:
        return await database.find(
            cls, (Field.workflow == workflow_name), limit=n_rows, sort=("started_at", "desc")
        )

    @classmethod
    async def get_by_age(
        cls: type[T],
        database: BaseStorage,
        age: timedelta,
        workflow_name: str | None = None,
    ) -> list[T]:
        query = Field.finished_at < (datetime.utcnow() - age)

        if workflow_name:
            query &= Field.workflow == workflow_name

        return await database.find(cls, query)

    def set_finished(
        self, result: Any | None = None, state: WorkflowRunState = WorkflowRunState.finished
    ) -> None:
        self.result = result
        self.finished_at = datetime.utcnow()

        self.set_state(state)

    def set_state(self, state: WorkflowRunState) -> None:
        self.state = state
