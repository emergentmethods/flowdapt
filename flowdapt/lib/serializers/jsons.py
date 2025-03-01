from typing import Any

import orjson
import rapidjson

from flowdapt.lib.serializers.base import Serializer


class JSONSerializer(Serializer):
    """
    Serializer for JSON data.
    """

    @staticmethod
    def loads(data: bytes) -> Any:
        return rapidjson.loads(
            data, parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
        )

    @staticmethod
    def dumps(data: Any) -> bytes:
        return rapidjson.dumps(data, write_mode=rapidjson.WM_PRETTY, indent=4).encode()


class ORJSONSerializer(Serializer):
    """
    Serializer for JSON data using ORJSON.
    """

    @staticmethod
    def loads(data: bytes) -> Any:
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif not isinstance(data, bytes):
            data = str(data).encode("utf-8")

        return orjson.loads(data)

    @staticmethod
    def dumps(data: Any) -> bytes:
        return orjson.dumps(data, option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY)
