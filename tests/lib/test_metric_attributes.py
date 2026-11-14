"""
The metrics SDK keeps one series for every distinct set of attribute values an
instrument is recorded with, for as long as the process lives. These tests pin
the property that keeps that bounded: recording the same kind of thing again
(another run of a workflow, another event of a type) reuses the same attribute
values instead of adding new ones.
"""

import asyncio
from uuid import uuid4

import pytest

import flowdapt.compute.resources.workflow.methods as workflow_methods
from flowdapt.compute.resources.workflow.methods import create_workflow, run_workflow
from flowdapt.lib.rpc.eventbus import create_event_bus
from flowdapt.lib.rpc.eventbus.event import BaseEvent, Event, ResponseEvent
from tests.compute.workflow.test_methods import get_workflow_create_payload


CHANNEL = "metric_attribute_tests"


class Recorder:
    """Stands in for a counter or histogram and keeps the attributes it is given."""

    def __init__(self):
        self.attributes: list[dict] = []

    def add(self, amount, attributes=None):
        self.attributes.append(dict(attributes or {}))

    record = add

    def series(self) -> list[dict]:
        """The distinct attribute sets recorded, i.e. the series the SDK would keep."""
        distinct = {tuple(sorted(attributes.items())) for attributes in self.attributes}
        return [dict(items) for items in distinct]


async def wait_for_recordings(recorder: Recorder, count: int) -> None:
    for _ in range(200):
        if len(recorder.attributes) >= count:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"expected {count} recordings, got {len(recorder.attributes)}")


@pytest.fixture
async def event_bus():
    bus = await create_event_bus("memory://")
    bus._events_published = Recorder()
    bus._events_received = Recorder()
    bus._event_callback_latency = Recorder()

    async with bus:
        yield bus


def new_reply() -> ResponseEvent:
    # A reply goes out on a channel named after the request it answers
    correlation_id = uuid4().hex
    return ResponseEvent(
        correlation_id=correlation_id, channel=f"{correlation_id}-response", source="tests"
    )


async def test_published_events_share_one_series(event_bus):
    for _ in range(3):
        await event_bus.publish(Event(channel=CHANNEL, source="tests"))

    assert len(event_bus._events_published.attributes) == 3
    assert event_bus._events_published.series() == [
        {"event_type": "internal.base.event", "event_channel": CHANNEL, "event_source": "tests"}
    ]


async def test_published_replies_share_one_series(event_bus):
    for _ in range(3):
        await event_bus.publish(new_reply())

    assert len(event_bus._events_published.attributes) == 3
    assert event_bus._events_published.series() == [
        {
            "event_type": "internal.base.response",
            "event_channel": "$REPLY",
            "event_source": "tests",
        }
    ]


async def test_received_events_share_one_series(event_bus):
    async with event_bus.subscribe(CHANNEL):
        for _ in range(3):
            await event_bus.publish(Event(channel=CHANNEL, source="tests"))

        await wait_for_recordings(event_bus._events_received, 3)

    assert event_bus._events_received.series() == [
        {"channel": CHANNEL, "event_type": "internal.base.event", "event_source": "tests"}
    ]


async def test_received_replies_share_one_series(event_bus):
    for received in range(1, 4):
        reply = new_reply()

        async with event_bus.subscribe(reply.channel):
            await event_bus.publish(reply)
            await wait_for_recordings(event_bus._events_received, received)

    assert event_bus._events_received.series() == [
        {"channel": "$REPLY", "event_type": "internal.base.response", "event_source": "tests"}
    ]


async def test_event_callbacks_share_one_series(event_bus):
    class Callback:
        name = "test_callback"
        event_model = BaseEvent

        async def __call__(self, event):
            pass

    for event in (Event(channel=CHANNEL, source="tests"), new_reply(), new_reply()):
        await event_bus._fire_callbacks([Callback()], event)

    assert len(event_bus._event_callback_latency.attributes) == 3
    assert sorted(
        event_bus._event_callback_latency.series(), key=lambda series: series["event_type"]
    ) == [
        {
            "callback_name": "test_callback",
            "event_type": "internal.base.event",
            "event_channel": CHANNEL,
            "event_source": "tests",
        },
        {
            "callback_name": "test_callback",
            "event_type": "internal.base.response",
            "event_channel": "$REPLY",
            "event_source": "tests",
        },
    ]


async def test_workflow_runs_share_one_series(test_context, clear_db, monkeypatch):
    executed, execution_time = Recorder(), Recorder()
    monkeypatch.setattr(workflow_methods, "workflows_executed_count", executed)
    monkeypatch.setattr(workflow_methods, "workflow_execution_time", execution_time)

    name = "metric_attributes_workflow"
    await create_workflow(get_workflow_create_payload(name).to_model())

    for _ in range(3):
        await run_workflow(name, input={}, wait=True)

    for recorder in (executed, execution_time):
        assert len(recorder.attributes) == 3
        assert len(recorder.series()) == 1
        assert set(recorder.series()[0]) == {
            "workflow.uid",
            "workflow.name",
            "workflow.executor",
            "workflow.namespace",
            "workflow.run.source",
        }
