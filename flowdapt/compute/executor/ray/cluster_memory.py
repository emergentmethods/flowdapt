import os
from collections import defaultdict
from typing import Any

from ray import get, get_actor, put, remote

from flowdapt.compute.cluster_memory.base import ClusterMemory

# Module-level actor handle cache keyed by actor name.
# Ray actor handles are cheap to hold and safe to reuse across calls within
# the same process, so we pay the ray.get_actor() GCS round-trip only once.
_actor_handles: dict[str, Any] = {}


@remote
class RayClusterMemoryActor:
    def __init__(self):
        self._store = defaultdict(dict)

    def put(self, key: str, value: Any, namespace: str = "default"):
        if namespace not in self._store:
            self._store[namespace] = {}

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

    def exists(self, key: str, namespace: str = "default") -> bool:
        return key in self._store.get(namespace, {})

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
        actor_name = os.environ["CM_ACTOR_NAME"]
        if actor_name not in _actor_handles:
            _actor_handles[actor_name] = get_actor(actor_name, namespace="flowdapt")
        self.actor = _actor_handles[actor_name]

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

    def exists(self, key: str, *, namespace: str = "default") -> bool:
        return get(self.actor.exists.remote(key, namespace=namespace))
