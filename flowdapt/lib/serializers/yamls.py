from typing import Any

import yaml

from flowdapt.lib.serializers.base import Serializer


class YAMLSerializer(Serializer):
    """
    Serializer for YAML data.
    """

    @staticmethod
    def loads(data: bytes) -> Any:
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif not isinstance(data, bytes):
            raise TypeError("Input data must be bytes or str")

        return yaml.safe_load(data)

    @staticmethod
    def dumps(data: Any) -> bytes:
        return yaml.dump(data, encoding="utf-8")
