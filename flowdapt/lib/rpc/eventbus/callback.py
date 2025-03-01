import asyncio
from functools import partial
from typing import Any, Awaitable, Callable, Generic, ParamSpec, Type, TypeVar

from flowdapt.lib.rpc.eventbus.event import BaseEvent, Event
from flowdapt.lib.utils.asynctools import is_async_callable


P = ParamSpec("P")
R = TypeVar("R")

CallbackType = Callable[..., R | Awaitable[R]]


class EventCallback(Generic[P, R]):
    def __init__(
        self,
        _fn: CallbackType,
        channel: str,
        event_type: str = "event",
        event_model: Type[BaseEvent] = Event,
    ):
        if not callable(_fn):
            raise TypeError("`_fn` must be callable.")

        self._fn = _fn
        self._is_async = is_async_callable(self._fn)
        self._name = self._fn.__name__

        assert channel, "EventCallback `channel` must not be empty"
        assert event_type, "EventCallback `event_type` must not be empty"

        self.channel = channel
        self.event_type = event_type
        self.event_model = event_model

    @property
    def is_async(self) -> bool:
        return self._is_async

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"<EventCallback: {self.name} ({self.channel}:{self.event_type})>"

    def match_event_type(self, event_type: str) -> bool:
        if self.event_type == event_type or self.event_type == "$ALL":
            return True
        return False

    async def __call__(self, *args: P.args, **kwargs: P.kwargs):
        if not self.is_async:
            loop = asyncio.get_running_loop()
            return loop.run_in_executor(None, partial(self._fn, *args, **kwargs))
        else:
            return await self._fn(*args, **kwargs)


class CallbackGroup:
    def __init__(self, callback_cls: Type[EventCallback] = EventCallback, *args, **kwargs) -> None:
        self._callback_cls = callback_cls
        self._callbacks: dict[str, list[EventCallback]] = {}

    @property
    def callbacks(self):
        return self._callbacks

    @property
    def channels(self):
        return self._callbacks.keys()

    def add_group(self, group: "CallbackGroup"):
        for _, callbacks in group.callbacks.items():
            for callback in callbacks:
                self.register_callback(callback)

    def get_callbacks(self, channel: str, event_type: str) -> list[EventCallback]:
        return [
            callback
            for callback in self.callbacks.get(channel, [])
            if callback.match_event_type(event_type)
        ]

    def remove_callback(self, callback: EventCallback):
        self._callbacks[callback.channel].remove(callback)
        if not self._callbacks[callback.channel]:
            del self._callbacks[callback.channel]

    def register_callback(self, callback: EventCallback):
        if callback.channel in self._callbacks.keys():
            self._callbacks[callback.channel].append(callback)
        else:
            self._callbacks[callback.channel] = [callback]

    def add_callback(self, callback: CallbackType, event: Type[BaseEvent] = Event):
        self.register_callback(
            self._callback_cls(
                callback,
                event.__fields__["channel"].default,
                event.__fields__["type"].default,
                event,
            )
        )

    def add_wildcard_callback(
        self,
        callback: CallbackType,
    ):
        self.register_callback(self._callback_cls(callback, "$ALL", "$ALL", Event))

    def callback(self, event: Type[Event], all: bool = False) -> Callable[..., Any]:
        def decorator(func: CallbackType) -> CallbackType:
            if all:
                self.add_wildcard_callback(callback=func)
            else:
                self.add_callback(callback=func, event=event)
            return func

        return decorator
