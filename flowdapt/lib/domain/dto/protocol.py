from typing import Protocol

from flowdapt.lib.utils.model import BaseModel


class RequestDTO(Protocol):
    def to_model(self) -> BaseModel:
        ...


class ResponseDTO(Protocol):
    @classmethod
    def from_model(cls, model: BaseModel):
        ...


DTOPair = tuple[RequestDTO | None, ResponseDTO | None]
DTOMapping = dict[str, DTOPair]
