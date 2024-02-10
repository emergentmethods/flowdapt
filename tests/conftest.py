import pytest
import asyncio
import numpy as np
import re
from pathlib import Path
from unittest.mock import AsyncMock

from flowdapt.lib.config import Configuration, set_configuration, set_app_dir
from flowdapt.lib.database.storage.memory import InMemoryStorage
from flowdapt.lib.rpc import RPC
from flowdapt.lib.rpc.eventbus import create_event_bus
from flowdapt.lib.rpc.api import create_api_server
from flowdapt.lib.context import create_context
from flowdapt.lib.utils.taskset import TaskSet
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.executor.local import LocalExecutor
from flowdapt.builtins.utils import dummy_pandas_df


# Redefine `pytest-asyncio` event loop fixture for session scope
@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def mocked_api_server(session_mocker):
    session_mocker.patch('flowdapt.lib.rpc.api.server.NoSignalServer.serve', AsyncMock())
    return await create_api_server()


@pytest.fixture(scope="session")
async def test_context(mocked_api_server):
    """
    Fixture for an ApplicationContext required for testing
    services and service methods
    """
    config = Configuration()

    set_configuration(config)
    set_app_dir(Path(__file__).parent)

    database = InMemoryStorage()
    context = create_context(
        {
            "config": config,
            "database": database,
            "rpc": RPC(
                mocked_api_server,
                await create_event_bus("memory://")
            ),
            "task_set": TaskSet(),
            "executor": LocalExecutor(use_processes=False)
        }
    )

    async with context:
        async with database:
            await asyncio.sleep(1)
            yield context


@pytest.fixture(scope="function")
async def clear_db(test_context):
    # Used to ensure database is clean each test since we use a 
    # session scoped context
    db = test_context["database"]
    yield
    for collection in await db.list_collections():
        await db.drop_collection(collection)

@pytest.fixture(scope="function")
def example_workflow():
    return {
        "metadata": {
            "name": "test_workflow",
        },
        "spec": {
            "stages": [
                {
                    "name": "stage1",
                    "target": lambda: list(range(10))
                },
                {
                    "name": "stage2",
                    "target": lambda x: x ** 2,
                    "depends_on": ["stage1"],
                    "type": "parameterized",
                }
            ]
        }
    }


@pytest.fixture(scope="function")
def example_workflow_expected_result():
    return [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]


@pytest.fixture(scope="function")
def dummy_df_with_nans():
    """
    Fixture for a dummy pandas df used to test the ML pipeline
    """
    np.random.seed(seed=20)
    return dummy_pandas_df(rows=100, cols=200, withnans=True)


@pytest.fixture(scope="function")
def dummy_df_without_nans():
    """
    Fixture for a dummy pandas df used to test the ML pipeline
    """
    np.random.seed(seed=20)
    return dummy_pandas_df(rows=100, cols=200, withnans=False)

# TODO: add a pipefill fixture

def log_has_re(line, logs):
    """Check if line matches some caplog's message."""
    return any(re.match(line, message) for message in logs.messages)
