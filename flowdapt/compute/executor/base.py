from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


# from flowdapt.compute.resources.workflow.stage import BaseStage


@runtime_checkable
class Executor(Protocol):
    kind: str
    running: bool = False

    async def start(self): ...

    async def close(self): ...

    async def reload_environment(self): ...

    async def environment_info(self): ...

    async def __call__(self, definition, run, context) -> Any: ...

    def lazy(self, stage) -> Any: ...

    def mapped_lazy(self, stage) -> Any: ...
