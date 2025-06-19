import pytest
import asyncio

from flowdapt.compute.executor.local.cluster_memory import (
    ClusterMemoryServer,
    ClusterMemoryClient,
)

TEST_SOCKET_PATH = "/tmp/test_cluster_memory.sock"


@pytest.fixture
async def cluster_memory_server():
    server = ClusterMemoryServer(TEST_SOCKET_PATH)
    await server.start()
    yield server
    await server.close()

@pytest.fixture
def cluster_memory_client() -> ClusterMemoryClient:
    return ClusterMemoryClient(TEST_SOCKET_PATH)


@pytest.mark.asyncio
async def test_local_cluster_memory_aput_aget(cluster_memory_server: ClusterMemoryServer, cluster_memory_client: ClusterMemoryClient):
    # Test default
    await cluster_memory_client.aput("test_key", "test_value")
    assert (await cluster_memory_client.aget("test_key")) == "test_value"

    # Test using a different namespace
    await cluster_memory_client.aput("test_key2", "test_value2", namespace="test_namespace")
    assert (await cluster_memory_client.aget("test_key2", namespace="test_namespace")) == "test_value2"
    
    with pytest.raises(KeyError):
        await cluster_memory_client.aget("test_key2")


@pytest.mark.asyncio
async def test_local_cluster_memory_delete(cluster_memory_server: ClusterMemoryServer, cluster_memory_client: ClusterMemoryClient):
    await cluster_memory_client.aput("test_key", "test_value")
    assert (await cluster_memory_client.aget("test_key")) == "test_value"
    assert (await cluster_memory_client.adelete("test_key")) == "OK"

    with pytest.raises(KeyError):
        await cluster_memory_client.aget("test_key")


@pytest.mark.asyncio
async def test_local_cluster_memory_clear(cluster_memory_server: ClusterMemoryServer, cluster_memory_client: ClusterMemoryClient):
    await cluster_memory_client.aput("test_key", "test_value")
    await cluster_memory_client.aput("test_key2", "test_value2", namespace="test_namespace")
    assert (await cluster_memory_client.aget("test_key")) == "test_value"
    assert (await cluster_memory_client.aget("test_key2", namespace="test_namespace")) == "test_value2"
    await cluster_memory_client.aclear()

    with pytest.raises(KeyError):
        await cluster_memory_client.aget("test_key")
        await cluster_memory_client.aget("test_key2", namespace="test_namespace")


@pytest.mark.asyncio
async def test_local_cluster_memory_exists(cluster_memory_server: ClusterMemoryServer, cluster_memory_client: ClusterMemoryClient):
    await cluster_memory_client.aput("test_key", "test_value")
    assert await cluster_memory_client.aexists("test_key") is True
    assert await cluster_memory_client.aexists("non_existent_key") is False

    await cluster_memory_client.aput("test_key2", "test_value2", namespace="test_namespace")
    assert await cluster_memory_client.aexists("test_key2", namespace="test_namespace") is True
    assert await cluster_memory_client.aexists("non_existent_key2", namespace="test_namespace") is False


@pytest.mark.asyncio
async def test_local_cluster_memory_invalid_operation(cluster_memory_server: ClusterMemoryServer, cluster_memory_client: ClusterMemoryClient):
    with pytest.raises(ValueError) as e:
        await cluster_memory_client.send_request({"operation": "invalid_operation", "args": []})

    assert str(e.value) == "Invalid operation: invalid_operation"
