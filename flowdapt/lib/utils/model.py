# flake8: noqa
from warnings import simplefilter
from typing import TypeVar, Callable, Any, TypeGuard, Generic, Annotated
from functools import partial
from pydantic import (
    BaseModel as PydanticBaseModel,
    ConfigDict,
    Field,
    ValidationError,
    PrivateAttr,
)
from pydantic.version import VERSION as PYDANTIC_VERSION
from manifest.pydantic import (
    get_model_extras,
    get_fields,
    get_set_fields,
    model_copy,
    model_dump
)

simplefilter("ignore", UserWarning)

T = TypeVar("T")

IS_V1 = PYDANTIC_VERSION.startswith("1.")

if IS_V1:
    from pydantic.main import ModelMetaclass
    from pydantic import root_validator, validator, create_model
    from pydantic.generics import GenericModel

    class RootModel(GenericModel, Generic[T]):
        __root__: T

        def __init__(self, data: T) -> None:
            super().__init__(__root__=data)

        @property
        def root(self) -> T:
            return self.__root__

        @root.setter
        def root(self, value: T) -> None:
            self.__root__ = value

        def __repr__(self) -> str:
            return f"root={self.__root__!r}"

        def dict(self, **kwargs) -> Any:
            return super().dict(**kwargs).get("__root__")

    class CallableOrImportString(str):
        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, v):
            if isinstance(v, Callable):
                return v
            return str(v)

        @classmethod
        def __modify_schema__(cls, field_schema):
            field_schema.update(type='string')

    class BaseModel(PydanticBaseModel):
        ...

    model_schema = lambda cls, *args, **kwargs: cls.schema(*args, **kwargs)
    pre_validator = partial(root_validator, pre=True, allow_reuse=True)
    after_validator = partial(root_validator, pre=False, allow_reuse=True)
    field_validator = validator
    validate_model = lambda cls, *args, **kwargs: cls.parse_obj(*args, **kwargs)
    from_orm = lambda cls, *args, **kwargs: cls.from_orm(*args, **kwargs)

    def PlainSerializer(*args, **kwargs):
        ...

else:
    from pydantic._internal._model_construction import ModelMetaclass
    from pydantic import (
        GetCoreSchemaHandler,
        GetJsonSchemaHandler,
        model_validator,
        field_validator,
        create_model,
        RootModel,
    )
    from pydantic.json_schema import JsonSchemaValue, model_json_schema
    from pydantic_core import CoreSchema, core_schema
    from pydantic.functional_serializers import PlainSerializer

    CallableOrImportString = Annotated[
        str | Callable,
        PlainSerializer(
            lambda x: x.__name__ if callable(x) else str(x),
            return_type=str,
            when_used='json'
        )
    ]

    class BaseModel(PydanticBaseModel):
        model_config = ConfigDict(from_attributes=True)

    pre_validator = partial(model_validator, mode="before")
    after_validator = partial(model_validator, mode="after")
    validate_model = lambda cls, *args, **kwargs: cls.model_validate(*args, **kwargs)
    from_orm = validate_model
    model_schema = model_json_schema


def is_pydantic_model(value: type) -> TypeGuard[BaseModel]:
    if isinstance(value, type) and (issubclass(value, BaseModel) or BaseModel in value.__mro__):
        return True
    elif isinstance(value, BaseModel):
        return True
    return False

def is_root_model(value: object) -> TypeGuard[RootModel]:
    if isinstance(value, RootModel) or (issubclass(value, RootModel) or RootModel in value.__mro__):
        return True
    elif isinstance(value, RootModel):
        return True
    return False


__all__ = (
    "CallableOrImportString",
    "get_model_extras",
    "get_fields",
    "get_set_fields",
    "BaseModel",
    "RootModel",
    "Field",
    "ModelMetaclass",
    "pre_validator",
    "field_validator",
    "PlainSerializer",
    "ConfigDict",
    "ValidationError",
    "PrivateAttr",
    "model_dump",
    "model_copy",
    "model_schema",
    "create_model",
    "is_pydantic_model",
    "is_root_model",
)
