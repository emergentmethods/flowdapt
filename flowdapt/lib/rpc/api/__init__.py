from fastapi import Request as Request

from flowdapt.lib.rpc.api.server import APIRouter as APIRouter
from flowdapt.lib.rpc.api.server import APIServer as APIServer


async def create_api_server(
    host: str = "127.0.0.1", port: int = 8080, *args, **kwargs
) -> APIServer:
    return APIServer(host, port, *args, **kwargs)


__all__ = ("APIServer", "APIRouter", "Request", "create_api_server")
