from flowdapt.lib.domain.dto.protocol import RequestDTO, ResponseDTO
from flowdapt.lib.domain.models.base import Resource
from flowdapt.lib.utils.model import (
    BaseModel,
    get_fields,
    is_pydantic_model,
    model_schema,
)


schema_registry = {}
REF_TEMPLATE = "#/components/schemas/{model}"


def get_schema(model: type[BaseModel], drop_definitions: bool = True) -> dict:
    """
    Get the schema for a Pydantic model

    :param model: The Pydantic model
    :param drop_definitions: Whether to drop the definitions section of the schema
    :return: The schema
    """
    schema = model_schema(model, ref_template=REF_TEMPLATE)
    if drop_definitions:
        schema.pop("definitions", None)
    return schema


def register_schema(model: type[BaseModel]) -> None:
    """
    Recursively register a Pydantic model and all of its fields
    in the schema registry

    :param model: The Pydantic model
    """
    if model.__name__ not in schema_registry:
        schema_registry[model.__name__] = get_schema(model)

        for field in get_fields(model).values():
            if is_pydantic_model(field.annotation):
                register_schema(field.annotation)


def ref_schema(model: type[BaseModel]):
    """
    Create a reference section for a Pydantic model

    :param model: The Pydantic model
    """
    return {"$ref": REF_TEMPLATE.format(model=model.__name__)}


class SupportedVersions:
    def __init__(self, *versions: str):
        self.versions = versions

    def __contains__(self, version: str):
        return version in self.versions

    def latest(self):
        return self.versions[-1]


def from_model(model: Resource, dto: ResponseDTO) -> ResponseDTO:
    return dto.from_model(model)


def to_model(dto: RequestDTO) -> Resource:
    return dto.to_model()
