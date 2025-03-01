from abc import ABC, abstractmethod
from typing import Tuple, Type

from flowdapt.lib.rpc.eventbus.event import BaseEvent
from flowdapt.lib.serializers import ORJSONSerializer, Serializer


class Broker(ABC):
    def __init__(self, _serializer: Type[Serializer] = ORJSONSerializer, *args, **kwargs):
        self._serializer = _serializer()

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the broker
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close the connection to the broker
        """
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> None:
        """
        Subscribe to a specific channel

        :param channel: The name of the channel to subscribe to
        :type channel: str
        """
        ...

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a specific channel

        :param channel: The name of the channel to unsubscribe
        :type channel: str
        """
        ...

    @abstractmethod
    async def publish(self, event: BaseEvent | dict) -> None:
        """
        Publish an event to a given channel

        :param event: The Event to publish
        :type event: Event
        """
        ...

    @abstractmethod
    async def next(self) -> Tuple[str, dict]:
        """
        Get the next event from the broker
        """
        ...
