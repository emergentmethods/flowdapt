from __future__ import annotations

from enum import Enum

from flowdapt.lib.database.base import BaseStorage, Field
from flowdapt.lib.domain.models.base import Resource
from flowdapt.lib.utils.model import BaseModel


CONFIG_RESOURCE_KIND = "config"


class ConfigSelectorType(str, Enum):
    name = "name"
    annotation = "annotation"


class ConfigSelector(BaseModel):
    kind: str | None = None
    type: ConfigSelectorType = "name"
    value: str | dict[str, str] | None


class ConfigSpec(BaseModel):
    selector: ConfigSelector | None = None
    data: dict


class ConfigResource(Resource):
    kind: str = CONFIG_RESOURCE_KIND
    spec: ConfigSpec

    @classmethod
    async def get_configs(cls, database: BaseStorage, resource: Resource) -> list[ConfigResource]:
        """
        Get all configs associated with a Resource.

        :param resource: The resource to match configs against
        :return: A list of configs that match the resource
        """
        by_name = await database.find(
            cls,
            (Field.spec.selector.exists())
            & (Field.spec.selector.kind.is_any([resource.kind, None]))
            & (Field.spec.selector.type == "name")
            & (Field.spec.selector.value == resource.metadata.name),
        )

        # Query for configs with a selector matching any of the annotations
        # specified in the value dict
        if resource.metadata.annotations:
            by_annotation = await database.find(
                cls,
                (Field.spec.selector.exists())
                & (Field.spec.selector.kind.is_any([resource.kind, None]))
                & (Field.spec.selector.type == "annotation")
                & (Field.spec.selector.value.partial(resource.metadata.annotations)),
            )
        else:
            by_annotation = []

        return by_name + by_annotation
