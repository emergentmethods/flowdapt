import re
from datetime import datetime
from typing import Annotated, TypeVar
from uuid import UUID, uuid4

from flowdapt.lib.database.annotations import Immutable
from flowdapt.lib.database.base import BaseStorage, Document, Field
from flowdapt.lib.utils.mixins.active_record import ActiveRecordMixin
from flowdapt.lib.utils.model import BaseModel, field_validator
from flowdapt.lib.utils.model import Field as PydanticField


T = TypeVar("T")


class ResourceMetadata(BaseModel):
    uid: Annotated[UUID, Immutable] = PydanticField(default_factory=uuid4)
    name: str
    created_at: Annotated[datetime, Immutable] = PydanticField(default_factory=datetime.utcnow)
    updated_at: datetime = PydanticField(default_factory=datetime.utcnow)
    annotations: dict[str, str] = {}

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value:
            raise ValueError("name cannot be empty")

        if not re.match(r"^[A-Za-z0-9_\-]+$", value):
            raise ValueError(
                "`name` can only contain alphanumeric characters, underscores, and hyphens."
            )

        return value


class Resource(Document, ActiveRecordMixin):
    kind: Annotated[str, Immutable]
    metadata: ResourceMetadata
    spec: dict

    async def _insert_before(self, database: BaseStorage):
        query = Field.metadata.name == self.metadata.name

        if await database.find_one(self, query):
            raise ValueError(
                f"{self.collection_name} with name `{self.metadata.name}` already exists"
            )

    async def _update_before(self, database: BaseStorage, source: dict | None = None):
        self.metadata.updated_at = datetime.utcnow()

        internal_annotations = {
            key: value
            for key, value in self.metadata.annotations.items()
            if key.startswith("flowdapt.ai/")
        }

        if internal_annotations:
            if source is None:
                source = {}

            if "metadata" not in source:
                source["metadata"] = {}
            if "annotations" not in source["metadata"]:
                source["metadata"]["annotations"] = {}

            source["metadata"]["annotations"].update(internal_annotations)

    @classmethod
    async def _get(cls: type[T], database: BaseStorage, identifier: str | UUID) -> T | None:
        if isinstance(identifier, str):
            try:
                identifier = UUID(identifier)
            except ValueError:
                pass

        return await database.find_one(
            cls,
            (Field.metadata.uid == identifier) | (Field.metadata.name == identifier),
        )
