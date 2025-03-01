from typing import Annotated, Any, Generic, TypeVar, get_args, get_origin, get_type_hints

from flowdapt.lib.database.annotations import Immutable
from flowdapt.lib.utils.model import BaseModel, is_pydantic_model


T = TypeVar("T")


class classproperty(property, Generic[T]):
    def __get__(self, owner_self, owner_cls: T) -> T:
        return self.fget(owner_cls)


def get_nested_field(obj: Any, fields: list) -> Any:
    """
    Recursively fetch nested fields given a list of field names.
    """
    if not isinstance(fields, list):
        fields = [fields]

    for part in fields:
        if isinstance(part, int):
            obj = obj[part]
        elif isinstance(obj, dict):
            obj = obj.get(part, None)
        elif isinstance(obj, list):
            obj = [item.get(part, None) if isinstance(item, dict) else None for item in obj]
        else:
            obj = getattr(obj, part, None)
    return obj


def is_immutable_field(field_type: type) -> bool:
    """
    Determine if a field type is annotated as Immutable.
    """
    return get_origin(field_type) == Annotated and Immutable in get_args(field_type)


def find_immutable_fields(model: type[BaseModel], base_path: tuple = ()) -> dict[tuple, bool]:
    immutable_fields = {}
    type_hints = get_type_hints(model, include_extras=True)

    for field_name, field_type in type_hints.items():
        full_field_path = base_path + (field_name,)

        if is_immutable_field(field_type):
            immutable_fields[full_field_path] = True
        elif is_pydantic_model(field_type):
            immutable_fields.update(find_immutable_fields(field_type, full_field_path))

    return immutable_fields


def merge(
    model: BaseModel, patch: dict, immutable_fields: dict[tuple, bool], base_path: tuple = ()
) -> None:
    for key, value in patch.items():
        full_field_path = base_path + (key,)

        if immutable_fields.get(full_field_path) and getattr(model, key) is not None:
            continue

        if isinstance(value, dict) and is_pydantic_model(type(getattr(model, key, None))):
            merge(getattr(model, key), value, immutable_fields, full_field_path)
        elif hasattr(model, key):
            setattr(model, key, value)
