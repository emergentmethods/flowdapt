import pytest
import numpy as np
import pandas as pd
import dask.array as da
from distributed import Client

from flowdapt.lib.utils.misc import get_full_path_type
from flowdapt.compute.executor.dask.cluster_memory import DaskClusterMemory


# TODO: Make this a module scope and just clear memory after each test?
@pytest.fixture(scope='function', autouse=True)
def dask_local_cluster():
    # Starting local Dask cluster
    with Client() as client:
        yield client


@pytest.fixture
def cluster_memory() -> DaskClusterMemory:
    return DaskClusterMemory()


def test_dask_cluster_memory_put_get(dask_local_cluster, cluster_memory: DaskClusterMemory):
    test_value = da.ones((1000, 1000), chunks=(100, 100))
    test_value_small = da.ones((100, 100), chunks=(100, 100))

    # Test putting and getting a value with and without namespace
    cluster_memory.put('test_key', test_value)
    cluster_memory.put('test_key', test_value_small, namespace='test_namespace')

    value = cluster_memory.get('test_key')
    assert get_full_path_type(value) == get_full_path_type(test_value)
    assert (value.compute() == test_value.compute()).all()

    value = cluster_memory.get('test_key', namespace='test_namespace')
    assert get_full_path_type(value) == get_full_path_type(test_value)
    assert (value.compute() == test_value_small.compute()).all()

    # Test using simple collections like numpy and pandas
    test_value_numpy = np.ones((1000, 1000))
    cluster_memory.put('test_key_numpy', test_value_numpy)
    value = cluster_memory.get('test_key_numpy')
    assert get_full_path_type(value) == get_full_path_type(test_value_numpy)
    assert (value == test_value_numpy).all()

    test_value_pandas = pd.DataFrame(np.ones((1000, 1000)))
    cluster_memory.put('test_key_pandas', test_value_pandas)
    value = cluster_memory.get('test_key_pandas')
    assert get_full_path_type(value) == get_full_path_type(test_value_pandas)
    assert (value == test_value_pandas).all().all()


def test_dask_cluster_memory_delete(dask_local_cluster, cluster_memory: DaskClusterMemory):
    test_value = da.ones((1000, 1000), chunks=(100, 100))
    test_value_small = da.ones((100, 100), chunks=(100, 100))

    cluster_memory.put('test_key', test_value)
    cluster_memory.put('test_key', test_value_small, namespace='test_namespace')

    cluster_memory.delete('test_key')

    with pytest.raises(Exception):
        cluster_memory.get('test_key')

    value = cluster_memory.get('test_key', namespace='test_namespace').compute()
    assert (value == test_value_small.compute()).all()


def test_dask_cluster_memory_clear(dask_local_cluster, cluster_memory: DaskClusterMemory):
    test_value1 = da.ones((1000, 1000), chunks=(100, 100))
    test_value2 = da.zeros((1000, 1000), chunks=(100, 100))
    test_value3 = da.ones((100, 100), chunks=(100, 100))

    cluster_memory.put('test_key1', test_value1)
    cluster_memory.put('test_key2', test_value2)
    cluster_memory.put('test_key3', test_value3, namespace='test_namespace')

    cluster_memory.clear()

    with pytest.raises(Exception):
        cluster_memory.get('test_key1')

    with pytest.raises(Exception):
        cluster_memory.get('test_key2')

    with pytest.raises(Exception):
        cluster_memory.get('test_key3', namespace='test_namespace')


def test_dask_cluster_memory_exists(dask_local_cluster, cluster_memory: DaskClusterMemory):
    test_value = da.ones((1000, 1000), chunks=(100, 100))
    test_value_small = da.ones((100, 100), chunks=(100, 100))

    cluster_memory.put('test_key', test_value)
    cluster_memory.put('test_key', test_value_small, namespace='test_namespace')

    assert cluster_memory.exists('test_key')
    assert cluster_memory.exists('test_key', namespace='test_namespace')

    cluster_memory.delete('test_key')
    assert not cluster_memory.exists('test_key')

    value = cluster_memory.get('test_key', namespace='test_namespace').compute()
    assert (value == test_value_small.compute()).all()
