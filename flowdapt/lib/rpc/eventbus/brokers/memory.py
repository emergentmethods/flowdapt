import asyncio
from typing import Tuple

from flowdapt.lib.rpc.eventbus.brokers.base import Broker
from flowdapt.lib.rpc.eventbus.event import BaseEvent
from flowdapt.lib.utils.model import model_dump


class MemoryBroker(Broker):
    """
    An in-memory queue broker
    """

    _channels: set[str] = set()
    _consumer: asyncio.Queue[tuple[str, dict]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def connect(self) -> None:
        self._consumer = asyncio.Queue()

    async def disconnect(self) -> None:
        pass

    async def subscribe(self, channel: str) -> None:
        self._channels.add(channel)

    async def unsubscribe(self, channel: str) -> None:
        if channel in self._channels:
            self._channels.remove(channel)

    async def publish(self, event: BaseEvent | dict, **kwargs) -> None:
        if isinstance(event, BaseEvent):
            event = model_dump(event)

        channel = event["channel"]
        assert channel, "Must specify a channel in the Event"

        await self._consumer.put((channel, event))

    async def next(self) -> Tuple[str, dict]:
        while True:
            channel, event = await self._consumer.get()
            if channel in self._channels:
                return channel, event
