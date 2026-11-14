import pytest
import ray
import os
import psutil

from flowdapt.compute.executor.ray.cluster_memory import (
    RayClusterMemory,
    RayClusterMemoryActor,
)

import time

@pytest.fixture(scope='module', autouse=True)
def ray_local_cluster():
    os.environ["CM_ACTOR_NAME"] = "RayClusterMemoryActor"
    # Initializing Ray with local mode
    ray.init(namespace="flowdapt")
    RayClusterMemoryActor.start(actor_name=os.environ["CM_ACTOR_NAME"])
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


def test_ray_cluster_memory_exists(cluster_memory: RayClusterMemory):
    cluster_memory.put('test_key', 'test_value')
    cluster_memory.put('test_key', 'test_value2', namespace='test_namespace')

    assert cluster_memory.exists('test_key')
    assert cluster_memory.exists('test_key', namespace='test_namespace')
    cluster_memory.delete('test_key')
    assert not cluster_memory.exists('test_key')

    assert cluster_memory.get('test_key', namespace='test_namespace') == 'test_value2'


def test_ray_cluster_memory_value_outlives_the_worker_that_put_it(
    cluster_memory: RayClusterMemory
):
    # `max_calls=1` makes the worker process exit once it has run this task
    @ray.remote(max_calls=1)
    def put_from_short_lived_worker(actor_name: str) -> int:
        os.environ["CM_ACTOR_NAME"] = actor_name
        # Large enough to live in the object store rather than be inlined
        RayClusterMemory().put('from_worker', 'x' * 1_000_000)
        return os.getpid()

    worker_pid = ray.get(put_from_short_lived_worker.remote(os.environ["CM_ACTOR_NAME"]))

    deadline = time.monotonic() + 30
    while psutil.pid_exists(worker_pid) and time.monotonic() < deadline:
        time.sleep(0.2)

    # The stored object belongs to the cluster memory actor, so it neither
    # keeps the worker that put it alive nor goes away with that worker
    assert not psutil.pid_exists(worker_pid)
    assert cluster_memory.get('from_worker') == 'x' * 1_000_000

