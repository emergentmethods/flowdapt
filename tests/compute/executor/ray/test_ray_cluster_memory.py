import pytest
import ray

from flowdapt.compute.executor.ray.cluster_memory import (
    RayClusterMemory,
    RayClusterMemoryActor,
)

import time

@pytest.fixture(scope='module', autouse=True)
def ray_local_cluster():
    # Initializing Ray with local mode
    ray.init(namespace="flowdapt")
    RayClusterMemoryActor.start()
    # somehow a delay is needed or else the tests cant find the actor
    time.sleep(1)
    yield
    ray.shutdown()


@pytest.fixture
def cluster_memory() -> RayClusterMemory:
    return RayClusterMemory()


def test_ray_cluster_memory_put_get(cluster_memory: RayClusterMemory):
    cluster_memory.put('test_key', 'test_value')
    cluster_memory.put('test_key', 'test_value2', namespace='test_namespace')
    assert cluster_memory.get('test_key') == 'test_value'
    assert cluster_memory.get('test_key', namespace='test_namespace') == 'test_value2'


def test_ray_cluster_memory_delete(cluster_memory: RayClusterMemory):
    cluster_memory.put('test_key', 'test_value')
    cluster_memory.put('test_key', 'test_value2', namespace='test_namespace')
    cluster_memory.delete('test_key')

    with pytest.raises(KeyError):
        cluster_memory.get('test_key')

    assert cluster_memory.get('test_key', namespace='test_namespace') == 'test_value2'


def test_ray_cluster_memory_clear(cluster_memory: RayClusterMemory):
    cluster_memory.put('test_key1', 'test_value1')
    cluster_memory.put('test_key2', 'test_value2')
    cluster_memory.put('test_key3', 'test_value3', namespace='test_namespace')
    cluster_memory.clear()

    with pytest.raises(KeyError):
        cluster_memory.get('test_key1')

    with pytest.raises(KeyError):
        cluster_memory.get('test_key2')

    with pytest.raises(KeyError):
        cluster_memory.get('test_key3', namespace='test_namespace')