import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import flowdapt.compute.service as compute_service
from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.compute.service import ComputeService
from flowdapt.lib.config import Configuration
from flowdapt.lib.database.storage.memory import InMemoryStorage
from flowdapt.lib.database.storage.tdb import TinyDBStorage


OLD = "finished-an-hour-ago"
RECENT = "finished-just-now"
RUNNING = "still-running"


@pytest.fixture(params=["memory", "tinydb"])
async def database(request, tmp_path):
    """
    A started storage holding one run that finished an hour ago, one that
    finished just now and one that is still running (no `finished_at`).
    """
    if request.param == "memory":
        storage = InMemoryStorage()
    else:
        storage = TinyDBStorage(path=str(tmp_path / "db.json"))

    now = datetime.utcnow()

    async with storage:
        await storage.insert(
            [
                WorkflowRun(
                    name=OLD,
                    workflow="workflow",
                    started_at=now - timedelta(hours=2),
                    finished_at=now - timedelta(hours=1),
                    state="finished",
                ),
                WorkflowRun(
                    name=RECENT,
                    workflow="workflow",
                    started_at=now - timedelta(seconds=5),
                    finished_at=now,
                    state="finished",
                ),
                WorkflowRun(
                    name=RUNNING,
                    workflow="workflow",
                    started_at=now - timedelta(hours=2),
                    state="running",
                ),
            ]
        )
        yield storage


class LogRecorder:
    def __init__(self):
        self.errors = []

    async def ainfo(self, event, **kwargs):
        pass

    async def aerror(self, event, **kwargs):
        self.errors.append((event, kwargs))


@pytest.fixture
def service_log(monkeypatch):
    recorder = LogRecorder()
    monkeypatch.setattr(compute_service, "logger", recorder)
    return recorder


async def run_names(database) -> list[str]:
    return sorted(run.name for run in await database.get_all(WorkflowRun))


def start_expiry_loop(database, retention) -> asyncio.Task:
    """
    Start the real expiry loop of the ComputeService. It only needs the
    config, the database and the stop event from the service.
    """
    config = Configuration(services={"compute": {"run_retention_duration": retention}})
    service = SimpleNamespace(_config=config, _db=database, _stopped=asyncio.Event())
    return asyncio.create_task(ComputeService._expire_workflow_runs(service))


async def stop(task: asyncio.Task) -> None:
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def test_get_by_age_only_returns_runs_that_finished_long_enough_ago(database):
    runs = await WorkflowRun.get_by_age(database, timedelta(minutes=1))

    assert [run.name for run in runs] == [OLD]


@pytest.mark.parametrize("retention", ["1m", 60])
async def test_expiry_loop_deletes_runs_older_than_the_retention(database, service_log, retention):
    task = start_expiry_loop(database, retention)

    try:
        # The first pass runs straight away, then the loop sleeps
        for _ in range(100):
            if OLD not in await run_names(database):
                break
            await asyncio.sleep(0.02)
    finally:
        await stop(task)

    assert service_log.errors == []
    assert await run_names(database) == sorted([RECENT, RUNNING])


@pytest.mark.parametrize("retention", [0, -1])
async def test_expiry_loop_does_nothing_when_retention_is_disabled(
    database, service_log, retention
):
    task = start_expiry_loop(database, retention)

    try:
        # There is nothing to expire, so the loop ends instead of polling
        await asyncio.wait_for(asyncio.shield(task), timeout=1)
    finally:
        await stop(task)

    assert service_log.errors == []
    assert await run_names(database) == sorted([OLD, RECENT, RUNNING])
