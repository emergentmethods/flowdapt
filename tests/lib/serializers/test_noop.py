import pytest

from flowdapt.lib.serializers import NoOpSerializer


@pytest.fixture
def dummy_data():
    return {"key": "value", "array": [1, 2, 3], "nested": {"key": "value"}}


@pytest.mark.parametrize(
    "serializer", [
        NoOpSerializer
    ]
)
def test_noop_serializer(serializer, dummy_data):
    # We don't expect NoOpSerializer to output bytes or anything since
    # nothing is serialized.
    data = serializer.dumps(dummy_data)
    assert serializer.loads(data) == dummy_data