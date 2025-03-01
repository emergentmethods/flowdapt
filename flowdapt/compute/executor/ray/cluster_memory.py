import os
from collections import defaultdict
from typing import Any

from ray import get, get_actor, put, remote

from flowdapt.compute.cluster_memory.base import ClusterMemory


@remote
class RayClusterMemoryActor:
    def __init__(self):
        self._store = defaultdict(dict)

    def put(self, key: str, value: Any, namespace: str = "default"):
        self._store[namespace][key] = value

    def get(self, key: str, namespace: str = "default"):
        value = self._store[namespace].get(key)
        if not value:
            raise KeyError(f"Key {key} not found in cluster memory")
        return value

    def delete(self, key: str, namespace: str = "default"):
        if namespace in self._store and key in self._store[namespace]:
            del self._store[namespace][key]

            if not self._store[namespace]:
                del self._store[namespace]

    def clear(self):
        self._store = {}

    @classmethod
    def start(cls, actor_name: str, **options):
        try:
            get_actor(actor_name, namespace="flowdapt")
        except ValueError:
            RayClusterMemoryActor.options(
                name=actor_name, lifetime="detached", namespace="flowdapt", **options
            ).remote()


class RayClusterMemory(ClusterMemory):
    def __init__(self):
        self.actor = get_actor(os.environ["CM_ACTOR_NAME"], namespace="flowdapt")

    def put(self, key: str, value: Any, *, namespace: str = "default"):
        object_ref = put(value, _owner=self.actor)
        get(self.actor.put.remote(key, [object_ref], namespace=namespace))

    def get(self, key: str, *, namespace: str = "default"):
        obj_list = get(self.actor.get.remote(key, namespace=namespace))
        return get(obj_list[0])

    def delete(self, key: str, *, namespace: str = "default"):
        get(self.actor.delete.remote(key, namespace=namespace))

    def clear(self):
        get(self.actor.clear.remote())
