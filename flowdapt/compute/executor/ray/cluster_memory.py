import os
from collections import defaultdict
from typing import Any

from ray import get, get_actor, put, remote

from flowdapt.compute.cluster_memory.base import ClusterMemory

# Module-level actor handle cache keyed by actor name.
# Ray actor handles are cheap to hold and safe to reuse across calls within
# the same process, so we pay the ray.get_actor() GCS round-trip only once.
_actor_handles: dict[str, Any] = {}


# Ray gives ownership of a task's return values to whoever called the task.
# The cluster memory actor calls this one, so the copy it returns belongs to
# the actor and outlives the worker that asked for the put. Without that the
# object would be owned by the putting worker: it would be lost when that
# worker dies, and the worker could not exit while the object is in use.
#
# This replaces `ray.put(value, _owner=actor)`, which Ray removed in 2.56.
#
# - `num_cpus=0` so the copy can always be scheduled, even when every CPU is
#   taken by the tasks that are waiting on their put.
# - `max_retries=0` so a failed copy raises to the caller instead of being
#   re-run later, when the original object may already be gone.
# - The second return value lets the actor wait for the copy, and see its
#   failure, without ever loading the value into its own process.
@remote(num_cpus=0, max_retries=0, num_returns=2)
def _copy_for_caller(value: Any):
    return value, True


@remote
class RayClusterMemoryActor:
    def __init__(self):
        self._store = defaultdict(dict)

    def put(self, key: str, value: Any, namespace: str = "default"):
        """
        :param value: A list holding the ObjectRef of the value to store. It is
        wrapped in a list so that Ray hands the actor the reference rather than
        the value itself.
        """
        if namespace not in self._store:
            self._store[namespace] = {}

        # The caller keeps its own object alive until this method returns, so
        # for the duration of a put there are two copies in the object store.
        owned_ref, copied = _copy_for_caller.remote(value[0])
        get(copied)

        self._store[namespace][key] = [owned_ref]

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
        # This reference is owned by the current process. The actor stores a
        # copy that it owns itself (see `_copy_for_caller`), and this one is
        # released once the put has returned.
        object_ref = put(value)
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
