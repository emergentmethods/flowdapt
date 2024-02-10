from typing import Any

from flowdapt.lib.serializers.base import Serializer


class NoOpSerializer(Serializer):
    """
    NoOp serializer that returns data as-is.
    """
    @staticmethod
    def loads(data: Any) -> Any:
        return data

    @staticmethod
    def dumps(data: Any) -> Any:
        return data
