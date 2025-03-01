import asyncio
from contextlib import suppress
from typing import Tuple

import aio_pika

from flowdapt.lib.rpc.eventbus.brokers.base import Broker
from flowdapt.lib.rpc.eventbus.event import BaseEvent
from flowdapt.lib.utils.misc import model_dump


class RabbitMQBroker(Broker):
    """
    A RabbitMQ Broker
    """

    _channel_consumers: dict[str, asyncio.Task] = {}
    _inbound_queue: asyncio.Queue[tuple[str, dict]]
    _connection: aio_pika.abc.AbstractRobustConnection
    _producer: aio_pika.abc.AbstractChannel

    def __init__(self, url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url = url
        self._args = args
        self._kwargs = kwargs

    async def _consume_channel(self, queue: aio_pika.abc.AbstractQueue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    parsed_message = self._serializer.loads(message.body)
                    await self._inbound_queue.put((queue.name, parsed_message))

    async def connect(self) -> None:
        self._inbound_queue = asyncio.Queue()
        self._connection = await aio_pika.connect_robust(self._url, *self._args, **self._kwargs)
        self._producer = await self._connection.channel()

    async def disconnect(self) -> None:
        for channel in list(self._channel_consumers.keys()):
            await self.unsubscribe(channel)
        await self._connection.close()

    async def subscribe(self, channel: str) -> None:
        if not self._channel_consumers.get(channel):
            _channel = await self._connection.channel()
            _queue = await _channel.declare_queue(channel, auto_delete=True)

            self._channel_consumers[channel] = asyncio.create_task(self._consume_channel(_queue))

    async def unsubscribe(self, channel: str) -> None:
        if task := self._channel_consumers.get(channel):
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task

            del self._channel_consumers[channel]

    async def publish(self, event: BaseEvent | dict, headers: dict = {}, **kwargs) -> None:
        if isinstance(event, BaseEvent):
            event = model_dump(event)

        channel = event["channel"]
        assert channel, "Must specify a channel in the Event"

        serialized_event = self._serializer.dumps(event)

        await self._producer.default_exchange.publish(
            aio_pika.Message(body=serialized_event, headers=event["headers"], **kwargs),
            routing_key=channel,
            **kwargs,
        )

    async def next(self) -> Tuple[str, dict]:
        return await self._inbound_queue.get()
