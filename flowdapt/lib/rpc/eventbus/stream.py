import asyncio
import logging
from typing import AsyncIterator, Type

from flowdapt.lib.rpc.eventbus.event import BaseEvent, EndOfStream, Event


logger = logging.getLogger(__name__)


class StreamFinished(Exception): ...


class EventStream:
    def __init__(
        self,
        *,
        maxsize: int = 0,
        schemas: list[Type[BaseEvent]] | None = None,
        _default_schema: Type[BaseEvent] = Event,
    ) -> None:
        """
        Helper class to allow consuming events from an inbound queue as an iterator

        :param maxsize: The maxsize of the internal queue
        :type maxsize: int
        :param schemas: A list of BaseEvent Subclasses to validate Event schema against
        :type schemas: List[Type[BaseEvent]]
        """
        self._queue: asyncio.Queue[dict | EndOfStream] = asyncio.Queue(maxsize)
        self._event_schemas = {"_default": _default_schema}

        if schemas:
            self._event_schemas.update(
                dict((event.__fields__["type"].get_default(), event) for event in schemas)
            )

    def _validate_event_schema(self, event: dict) -> BaseEvent:
        # Determine the eligible event schema based on the "key" value
        # We don't want to raise any errors here so we default to the
        # _default key
        event_type = event["type"]
        model_cls = self._event_schemas.get(event_type) or self._event_schemas["_default"]

        # Validate the event against the schema
        return model_cls(**event)

    async def __aiter__(self) -> AsyncIterator[BaseEvent]:
        # Iterate over the event dicts in the queue and yield the
        # validated event
        # Finish iteration when StreamFinished is reached
        try:
            while event := await self.get():
                yield self._validate_event_schema(event)
        except (StreamFinished, asyncio.CancelledError):
            pass

    async def get(self) -> dict:
        """
        Get an Event dict from the stream. Raises StreamFinished when EndOfStream is encountered.
        """
        if (event := await self._queue.get()) and not isinstance(event, EndOfStream):
            self._queue.task_done()
            return event
        raise StreamFinished

    async def put(self, item: dict | EndOfStream):
        """
        Put an Event dict or EndOfStream on the stream.

        :param item: The Event dict or EndOfStream
        :type item: dict | EndOfStream
        """
        if not isinstance(item, dict) and not isinstance(item, EndOfStream):
            raise ValueError("`item` must be an Event dict or EndOfStream")

        await self._queue.put(item)

    async def close(self):
        """
        Signal a close to the stream with an EndOfStream
        """
        await self.put(EndOfStream())
