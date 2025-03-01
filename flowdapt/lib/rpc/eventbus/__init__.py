from flowdapt.lib.rpc.eventbus.bus import EventBus as EventBus
from flowdapt.lib.rpc.eventbus.callback import CallbackGroup as CallbackGroup
from flowdapt.lib.rpc.eventbus.callback import EventCallback as EventCallback
from flowdapt.lib.rpc.eventbus.event import BaseEvent as BaseEvent
from flowdapt.lib.rpc.eventbus.event import EndOfStream as EndOfStream
from flowdapt.lib.rpc.eventbus.event import Event as Event
from flowdapt.lib.rpc.eventbus.event import ResponseEvent as ResponseEvent
from flowdapt.lib.rpc.eventbus.stream import EventStream as EventStream
from flowdapt.lib.utils.misc import import_from_string


async def create_event_bus(url: str = "memory://", serializer: str = "msgpack", *args, **kwargs):
    from urllib.parse import urlparse

    _AVAILABLE_BROKERS = {
        "memory": lambda: import_from_string(
            "flowdapt.lib.rpc.eventbus.brokers.memory.MemoryBroker"
        ),  # noqa
        "amqp": lambda: import_from_string(
            "flowdapt.lib.rpc.eventbus.brokers.rabbitmq.RabbitMQBroker"
        ),  # noqa
    }
    _AVAILABLE_SERIALIZERS = {
        "msgpack": lambda: import_from_string("flowdapt.lib.serializers.MsgPackSerializer"),  # noqa
        "json": lambda: import_from_string("flowdapt.lib.serializers.ORJSONSerializer"),  # noqa
    }

    # Get broker from our available brokers based on the URL scheme
    parsed = urlparse(url)
    broker = _AVAILABLE_BROKERS[parsed.scheme]()

    kwargs.update({"_serializer": _AVAILABLE_SERIALIZERS[serializer](), "url": url})

    return EventBus(broker, *args, **kwargs)


__all__ = (
    "create_event_bus",
    "EventBus",
    "Event",
    "ResponseEvent",
    "EventCallback",
    "CallbackGroup",
    "BaseEvent",
    "EndOfStream",
    "StreamFinished",
    "EventStream",
)
