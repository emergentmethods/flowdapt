from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SentinelMeta(type):
    def __init__(cls, name, bases, dict):
        super(SentinelMeta, cls).__init__(name, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SentinelMeta, cls).__call__(*args, **kwargs)
        return cls._instance

    def __repr__(cls) -> str:
        return f"<{cls.__name__}>"

    def __bool__(cls) -> Literal[False]:
        return False


class EndOfStream(metaclass=SentinelMeta):
    pass


class BaseEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    time: datetime = Field(default_factory=datetime.now)
    headers: dict[str, Any] = {}
    correlation_id: str | None = None
    reply_channel: str | None = None
    trace_parent: str | None = None
    channel: str
    source: str
    type: str
    data: Any = None


class Event(BaseEvent):
    model_config = ConfigDict(extra="allow")

    type: str = "internal.base.event"


class ResponseEvent(Event):
    type: str = "internal.base.response"
    correlation_id: str
