from typing import Any

import msgpack

from flowdapt.lib.serializers.base import Serializer


class MsgPackSerializer(Serializer):
    @staticmethod
    def loads(data: bytes) -> Any:
        return msgpack.loads(data)

    @staticmethod
    def dumps(data: Any) -> bytes:
        return msgpack.dumps(data)
