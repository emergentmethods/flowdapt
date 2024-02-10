import pytest

from flowdapt.lib.serializers import YAMLSerializer


@pytest.fixture
def dummy_data():
    return {"key": "value", "array": [1, 2, 3], "nested": {"key": "value"}}


@pytest.mark.parametrize(
    "serializer", [
        YAMLSerializer
    ]
)
def test_yaml_serializers(serializer, dummy_data):
    data = serializer.dumps(dummy_data)
    assert isinstance(data, bytes), "Output is not bytes"
    assert serializer.loads(data) == dummy_data