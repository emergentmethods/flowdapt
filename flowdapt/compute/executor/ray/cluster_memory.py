import os
from collections import defaultdict
from typing import Any, Sequence, overload

from asyncer import asyncify
from ray import ObjectRef, get, get_actor, put, remote
from ray.actor import ActorHandle

from flowdapt.compute.cluster_memory.base import ClusterMemory


@overload
async def ray_get(
    object_refs: ObjectRef,
    *,
    timeout: float | None = None
) -> Any:
    ...

@overload
async def ray_get(
    object_refs: Sequence[ObjectRef],
    *,
    timeout: float | None = None
) -> list[Any]:
    ...


async def ray_get(
    object_refs: ObjectRef | Sequence[ObjectRef],
    *,
    timeout: float | None = None
) -> Any | list[Any]:
    return await asyncify(get)(object_refs, timeout=timeout)  # type: ignore[arg-type]


async def ray_put(
    value: Any,
    *,
    _owner: ActorHandle | None = None
) -> ObjectRef:
    return await asyncify(put)(value, _owner=_owner)


@remote
class RayClusterMemoryActor:
    def __init__(self) -> None:
        self._store: dict[str, dict] = defaultdict(dict)

    async def put(self, key: str, value: Any, namespace: str = "default") -> None:
        self._store[namespace][key] = value

    async def get(self, key: str, namespace: str = "default") -> int:
        value = self._store[namespace].get(key)
        if not value:
            raise KeyError(f"Key {key} not found in cluster memory")
        return value

    async def delete(self, key: str, namespace: str = "default") -> None:
        if namespace in self._store and key in self._store[namespace]:
            del self._store[namespace][key]

            if not self._store[namespace]:
                del self._store[namespace]

    async def list(self, prefix: str | None = None, namespace: str = "default") -> list[str]:
        if namespace not in self._store:
            return []

        if prefix is None:
            return list(self._store[namespace].keys())

        return [
            key
            for key in self._store[namespace]
            if key.startswith(prefix)
        ]

    async def exists(self, key: str, namespace: str = "default") -> bool:
        return key in self._store.get(namespace, {})

    async def clear(self, namespace: str | None = None) -> None:
        if namespace is not None and namespace in self._store:
            del self._store[namespace]
        else:
            self._store = defaultdict(dict)

    @classmethod
    def start(cls, actor_name: str, **options):
        try:
            get_actor(actor_name, namespace="flowdapt")
        except ValueError:
            RayClusterMemoryActor.options(  # type: ignore[attr-defined]
                name=actor_name, lifetime="detached", namespace="flowdapt", **options
            ).remote()


class RayClusterMemory(ClusterMemory):
    def __init__(self) -> None:
        self.actor: ActorHandle = get_actor(
            os.environ["CM_ACTOR_NAME"],
            namespace="flowdapt"
        )

    async def aget(self, key: str, *, namespace: str = "default") -> Any:
        return await self.actor.get.remote(key, namespace=namespace)

    async def aput(self, key: str, value: Any, *, namespace: str = "default") -> None:
        await self.actor.put.remote(
            key,
            await ray_put(value, _owner=self.actor),
            namespace=namespace
        )

    async def adelete(self, key: str, *, namespace: str = "default") -> None:
        await self.actor.delete.remote(key, namespace=namespace)

    async def alist(self, prefix: str | None = None, *, namespace: str = "default") -> list[str]:
        return await self.actor.list.remote(prefix, namespace=namespace)

    async def aexists(self, key: str, *, namespace: str = "default") -> bool:
        return await self.actor.exists.remote(key, namespace=namespace)

    async def aclear(self, *, namespace: str | None = None) -> None:
        await self.actor.clear.remote(namespace=namespace)
