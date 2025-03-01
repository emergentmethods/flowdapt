import asyncio
from contextlib import suppress
from enum import Enum
from typing import Any, Callable, Type

from flowdapt.lib.rpc.api import APIRouter, APIServer
from flowdapt.lib.rpc.eventbus import CallbackGroup, Event, EventBus
from flowdapt.lib.utils.misc import import_from_string


class RPC:
    """
    Main Service RPC manager object
    """

    def __init__(self, api_server: APIServer, event_bus: EventBus) -> None:
        assert asyncio.get_running_loop(), "RPC must be initialized inside an async method"

        self._api_server = api_server
        self._event_bus = event_bus

        self._lock = asyncio.Lock()
        self._disconnected = asyncio.Event()
        self._disconnected.set()

        self._api_server_task: asyncio.Task
        self._event_bus_task: asyncio.Task

    @property
    def api_server(self):
        return self._api_server

    @property
    def event_bus(self):
        return self._event_bus

    def add_spec(self, spec_path: str) -> None:
        spec = import_from_string(spec_path)
        self.add_rpc_router(spec)

    def add_rpc_router(self, router: "RPCRouter") -> None:
        self._api_server.add_router(router.api_router)
        self._event_bus.add_group(router.event_group)

    async def start(self) -> None:
        async with self._lock:
            self._api_server_task = asyncio.create_task(self._api_server.serve())
            await self._event_bus.connect()

            self._disconnected.clear()

    async def stop(self) -> None:
        async with self._lock:
            if self._api_server_task:
                await self._api_server.stop()

                with suppress(asyncio.CancelledError):
                    await self._api_server_task

            await self._event_bus.disconnect()
            self._disconnected.set()

    async def __aenter__(self) -> "RPC":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()

    async def wait_until_finished(self):
        return await self._disconnected.wait()


class RPCRouter:
    """
    RPC Router Facade to bring registering FastAPI endpoints and
    EventBus callbacks into a single interface.
    """

    def __init__(self, *args, **kwargs):
        self._api_router = APIRouter(*args, **kwargs)
        self._event_group = CallbackGroup(*args, **kwargs)

    @property
    def api_router(self) -> APIRouter:
        return self._api_router

    @property
    def event_group(self) -> CallbackGroup:
        return self._event_group

    def include_router(self, router: "RPCRouter"):
        # Include event callback group
        self._event_group.add_group(router.event_group)
        # Include the api router
        self._api_router.include_router(router.api_router)

    def add_api_route(
        self,
        path: str,
        *,
        method: str = "GET",
        response_model: Any = None,
        status_code: int | None = None,
        tags: list[str | Enum] | None = None,
        summary: str | None = None,
        description: str | None = None,
        response_description: str = "Successful Response",
        responses: dict[int | str, dict[str, Any]] | None = None,
        **kwargs,
    ):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._api_router.add_api_route(
                path=path,
                endpoint=func,
                response_model=response_model,
                status_code=status_code,
                tags=tags,
                summary=summary,
                description=description,
                response_description=response_description,
                responses=responses,
                methods=[method],
                **kwargs,
            )
            return func

        return decorator

    def add_event_callback(self, event: Type[Event] = Event, all: bool = False):
        return self._event_group.callback(event, all)
