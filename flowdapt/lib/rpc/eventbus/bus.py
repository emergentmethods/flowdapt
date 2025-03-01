import asyncio
from contextlib import asynccontextmanager, suppress
from time import process_time_ns
from typing import Any, AsyncIterator, Literal, Type, TypeVar

from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc.eventbus.brokers import Broker, MemoryBroker
from flowdapt.lib.rpc.eventbus.callback import CallbackGroup, EventCallback
from flowdapt.lib.rpc.eventbus.event import BaseEvent, Event, ResponseEvent
from flowdapt.lib.rpc.eventbus.stream import EventStream
from flowdapt.lib.telemetry import (
    ctx_from_parent,
    get_current_span,
    get_meter,
    get_trace_parent,
    get_tracer,
)
from flowdapt.lib.utils.misc import generate_uuid
from flowdapt.lib.utils.model import model_dump, validate_model


logger = get_logger(__name__)
tracer = get_tracer(__name__)
meter = get_meter(__name__)

TEventBus = TypeVar("TEventBus", bound="EventBus")


class EventBus:
    def __init__(
        self, broker: Type[Broker] = MemoryBroker, *args, concurrency_limit: int = 100, **kwargs
    ):
        assert asyncio.get_running_loop(), "EventBus must be instantiated with an active loop"

        self._broker = broker(*args, **kwargs)
        self._concurrency_limit = concurrency_limit

        self._lock = asyncio.Lock()
        self._disconnected = asyncio.Event()
        self._disconnected.set()

        self._consumer_task: asyncio.Task

        self._streams: dict[str, set[EventStream]] = {}
        self._callback_tasks: dict[str, set[asyncio.Task]] = {}
        self._callback_group: CallbackGroup = CallbackGroup()

        self._events_published = meter.create_counter(
            name="events_published", description="The number of events published", unit="1"
        )
        self._events_received = meter.create_counter(
            name="events_received", description="The number of events received", unit="1"
        )
        self._event_callback_latency = meter.create_histogram(
            name="event_callback_latency", description="The latency of event callbacks", unit="ms"
        )

    @property
    def connected(self) -> bool:
        return not self._disconnected.is_set()

    def _ensure_connected(self):
        if not self.connected:
            raise RuntimeError("Must call `.connect` on the EventBus")

    async def _consumer(self):
        # Iteratively get the incoming events and add them
        # to their respective streams
        while True:
            channel, event = await self._broker.next()
            self._events_received.add(
                1,
                {
                    "channel": channel,
                    "event_type": event.get("type"),
                    "event_source": event.get("source"),
                },
            )
            streams = self._streams.get(channel, set()) | self._streams.get("$ALL", set())

            for stream in streams:
                await stream.put(event)

    async def _create_callback_reader(self, channel):
        # Create callback reader task
        self._callback_tasks[channel] = asyncio.create_task(self._read_stream(channel))

    async def create_callback_reader(self, channel):
        async with self.lock:
            await self._create_callback_reader(channel)

    async def _read_stream(self, channel: str) -> None:
        # Subscribe to the channel and call the callbacks
        # for each event
        # Task will end when the stream is closed
        async with self.subscribe(channel) as stream:
            async for event in stream:
                await self._fire_callbacks(
                    self._callback_group.get_callbacks(channel, event.type), event
                )

    async def _fire_callbacks(self, callbacks: list[EventCallback], event: BaseEvent):
        # Run all callbacks sequentially. We could run them concurrently with
        # a limit using `gather_with_concurrency` but the callbacks wouldn't
        # execute in the same order as they were given. This may not be an issue
        # further testing is required.

        # return await gather_with_concurrency(
        #     self._concurrency_limit,
        #     *(callback(event) for callback in callbacks)
        # )

        for callback in callbacks:
            if not isinstance(event, callback.event_model):
                event = validate_model(callback.event_model, dict(event))

            try:
                if event.trace_parent:
                    ctx = ctx_from_parent(event.trace_parent)
                else:
                    ctx = get_current_span().get_span_context()  # type: ignore

                event_attributes = {
                    "callback_name": callback.name,
                    "event_type": event.type,
                    "event_channel": event.channel,
                    "event_id": str(event.id),
                    "event_correlation_id": event.correlation_id or "",
                    "event_reply_channel": event.reply_channel or "",
                    "event_source": event.source,
                }

                with tracer.start_as_current_span(
                    f"event_bus_callback_{callback.name}", context=ctx, attributes=event_attributes
                ):
                    start_time = process_time_ns()
                    await callback(event)
                    latency = (process_time_ns() - start_time) / 1e6

                    self._event_callback_latency.record(latency, event_attributes)
            except BaseException as e:
                await logger.aexception(
                    "Exception occurred",
                    callback=callback.name,
                    event_type=event.type,
                    error=str(e),
                )

    def add_group(self, group: CallbackGroup):
        """
        Add a CallbackGroup to the EventBus group

        :param group: The callback group to add
        :type group: CallbackGroup
        """
        assert isinstance(group, CallbackGroup)
        self._callback_group.add_group(group)

    async def connect(self) -> None:
        """
        Initiate the connection for the EventBus
        """
        async with self._lock:
            # As long as we aren't already connected
            if not self.connected:
                # Connect on the broker
                await self._broker.connect()

                # Create callback readers for each channel in group
                for channel in self._callback_group.channels:
                    await self._create_callback_reader(channel)

                # Create our reader task
                self._consumer_task = asyncio.create_task(self._consumer())

                # Set connected flag
                self._disconnected.clear()
                await asyncio.sleep(1)

    async def disconnect(self) -> None:
        """
        Disconnect the EventBus
        """
        async with self._lock:
            await self.close_streams()

            # Cancel task if not done
            if not self._consumer_task.done():
                self._consumer_task.cancel()

            # Retrieve result to satisfy asyncio gods
            with suppress(asyncio.CancelledError):
                await self._consumer_task

            await self._broker.disconnect()
            self._disconnected.set()

    async def __aenter__(self: TEventBus) -> TEventBus:
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()

    async def wait_until_finished(self) -> Literal[True]:
        return await self._disconnected.wait()

    async def _subscribe_channel(self, channel: str) -> None:
        await self._broker.subscribe(channel)

    async def _unsubscribe_channel(self, channel: str) -> None:
        await self._broker.unsubscribe(channel)

    async def _register_stream(self, channel: str, stream: EventStream) -> None:
        # Check if there is already a subscriber for this channel
        if not self._streams.get(channel):
            # If no existing subscriber, add one and subscribe on the broker
            await self._subscribe_channel(channel)
            self._streams[channel] = {
                stream,
            }
        else:
            # If there is, simply add it
            self._streams[channel].add(stream)

    async def register_stream(self, channel: str, stream: EventStream) -> None:
        async with self._lock:
            await self._register_stream(channel, stream)

    async def _deregister_stream(self, channel: str, stream: EventStream) -> None:
        # Get all of the subscriber stream for this channel
        if stream_set := self._streams.get(channel):
            # Remove it from the set
            stream_set.remove(stream)
            # If the set is now empty, we have no more subscribers for this channel
            if not stream_set:
                # Delete the set
                del self._streams[channel]
                # And unsubscribe from the broker
                await self._unsubscribe_channel(channel)

    async def deregister_stream(self, channel: str, stream: EventStream) -> None:
        async with self._lock:
            await self._deregister_stream(channel, stream)

    async def close_streams(self) -> None:
        # Put a Sentinel on all streams to close them
        for streams in self._streams.values():
            for stream in streams:
                await stream.close()

    async def publish(self, event: BaseEvent | dict, **kwargs) -> None:
        """
        Publish an Event to the Broker

        :param event: The Event to publish
        :type event: BaseEvent | dict
        """
        self._ensure_connected()

        if isinstance(event, BaseEvent):
            event = model_dump(event)

        event_attributes = {
            "event_type": event["type"],
            "event_channel": event["channel"],
            "event_id": str(event["id"]),
            "event_correlation_id": event["correlation_id"] or "",
            "event_reply_channel": event["reply_channel"] or "",
            "event_source": event["source"],
        }

        with tracer.start_as_current_span("event_bus_publish", attributes=event_attributes):
            if not event["trace_parent"]:
                event["trace_parent"] = get_trace_parent()

            # Publish the Event on the broker
            await self._broker.publish(event, **kwargs)
            # Increment the published counter
            self._events_published.add(1, event_attributes)

    async def publish_request_response(
        self, event: BaseEvent | dict, return_event: bool = False, **kwargs
    ) -> BaseEvent | None:
        """
        Send a Request style Event and wait for the
        response.

        :param event: The Event to publish
        :type event: BaseEvent | dict
        :returns: The ReplyEvent or None
        """
        if isinstance(event, BaseEvent):
            event = model_dump(event)

        if not event["correlation_id"]:
            event["correlation_id"] = generate_uuid()

        if not event["reply_channel"]:
            event["reply_channel"] = event["correlation_id"] + "-response"

        response_task = asyncio.create_task(
            self.watch_for_event(
                event["reply_channel"],
                {"correlation_id": event["correlation_id"]},
                event_type=ResponseEvent,
            )
        )

        await self.publish(event, **kwargs)

        if response := await response_task:
            if not return_event:
                return response.data
            else:
                return response
        return None

    async def publish_response(self, response: Any, reply_channel: str, correlation_id: str):
        """
        Publish a response to a Request style Event.

        :param response: The response to publish
        :type response: Any
        :param reply_channel: The channel to publish the reply on
        :type reply_channel: str
        :param correlation_id: The correlation ID
        :type correlation_id: str
        """
        await self.publish(
            ResponseEvent(correlation_id=correlation_id, channel=reply_channel, data=response)
        )

    @asynccontextmanager
    async def subscribe(self, channel: str, **kwargs) -> AsyncIterator[EventStream]:
        """
        Context manager to create an EventStream and subscribe to the specified channel.

        :param channel: The channel to subscribe to
        :type channel: str
        :param **kwargs: The keyword args to pass to the EventStream
        :type **kwargs: Any
        """
        self._ensure_connected()

        stream = EventStream(**kwargs)
        # Register the stream
        await self._register_stream(channel, stream)
        try:
            yield stream
        finally:
            # Put sentinel to signal end
            await stream.close()
            # Deregister the stream
            await self._deregister_stream(channel, stream)

    async def watch_for_event(
        self,
        channel: str,
        conditions: dict[str, Any] = {},
        event_type: Type[BaseEvent] = Event,
    ) -> BaseEvent | None:
        """
        Subscribe to a channel and watch for an event based on certain
        conditions.

        :param channel: The channel to subscribe to
        :type channel: str
        :param event_type: The Event class to look for
        :type event_type: Type[BaseEvent]
        :param conditions: A dictionary of event attributes and the expected values
        :type conditions: dict[str, Any]
        :returns: The matching Event or None if not found
        """
        async with self.subscribe(channel, schemas=[event_type]) as stream:
            async for event in stream:
                # For each event we see, if it's the correct type
                # and has all of the matching fields, then return it
                if all(
                    [
                        True if getattr(event, key) == value else False
                        for key, value in conditions.items()
                    ]
                ) and isinstance(event, event_type):
                    return event
        # Return None if for some reason the Event isn't found
        return None
