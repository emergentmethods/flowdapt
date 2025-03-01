import http
import os
import time
from typing import TypedDict
from urllib.parse import quote

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    HTTPScope,
)

from flowdapt.lib.logger import LoggerType


def get_client_addr(scope: HTTPScope):
    if scope["client"] is None:
        return "-"  # pragma: no cover
    return f"{scope['client'][0]}:{scope['client'][1]}"


def get_path_with_query_string(scope: HTTPScope) -> str:
    path_with_query_string = quote(scope.get("root_path", "") + scope["path"])
    if scope["query_string"]:  # pragma: no cover
        return f"{path_with_query_string}?{scope['query_string'].decode('ascii')}"
    return path_with_query_string


class AccessInfo(TypedDict, total=False):
    response: ASGISendEvent
    start_time: float
    end_time: float


class AccessLogAtoms(dict):
    def __init__(self, scope: HTTPScope, info: AccessInfo) -> None:
        for name, value in scope["headers"]:
            self[f"{{{name.decode('latin1').lower()}}}i"] = value.decode("latin1")
        for name, value in info["response"].get("headers", []):
            self[f"{{{name.decode('latin1').lower()}}}o"] = value.decode("latin1")
        for name, value in os.environ.items():
            self[f"{{{name.lower()!r}}}e"] = value

        protocol = f"HTTP/{scope['http_version']}"

        status = info["response"]["status"]
        try:
            status_phrase = http.HTTPStatus(status).phrase
        except ValueError:
            status_phrase = "-"

        path = scope["root_path"] + scope["path"]
        full_path = get_path_with_query_string(scope)
        request_line = f"{scope['method']} {path} {protocol}"
        full_request_line = f"{scope['method']} {full_path} {protocol}"

        request_time = info["end_time"] - info["start_time"]
        client_addr = get_client_addr(scope)
        self.update(
            {
                "h": client_addr,
                "client_addr": client_addr,
                "l": "-",
                "u": "-",  # Not available on ASGI.
                "t": time.strftime("[%d/%b/%Y:%H:%M:%S %z]"),
                "r": request_line,
                "request_line": full_request_line,
                "R": full_request_line,
                "m": scope["method"],
                "U": scope["path"],
                "q": scope["query_string"].decode(),
                "H": protocol,
                "s": status,
                "status_code": f"{status} {status_phrase}",
                "st": status_phrase,
                "B": self["{Content-Length}o"],
                "b": self.get("{Content-Length}o", "-"),
                "f": self["{Referer}i"],
                "a": self["{User-Agent}i"],
                "T": int(request_time),
                "M": int(request_time * 1_000),
                "D": int(request_time * 1_000_000),
                "L": f"{request_time:.6f}",
                "p": f"<{os.getpid()}>",
            }
        )

    def __getitem__(self, key: str) -> str:
        try:
            if key.startswith("{"):
                return super().__getitem__(key.lower())
            else:
                return super().__getitem__(key)
        except KeyError:
            return "-"


class AccessLoggerMiddleware:
    def __init__(self, app: ASGI3Application, logger: LoggerType):
        self._app = app
        self._logger = logger

    async def __call__(
        self, scope: HTTPScope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        if scope["type"] != "http":
            return await self._app(scope, receive, send)  # pragma: no cover

        info = AccessInfo(response={})

        async def inner_send(message: ASGISendEvent) -> None:
            if message["type"] == "http.response.start":
                info["response"] = message
            await send(message)

        try:
            info["start_time"] = time.time()
            await self._app(scope, receive, inner_send)
        except Exception as exc:
            info["response"]["status"] = 500
            raise exc
        finally:
            info["end_time"] = time.time()
            await self.log(scope, info)

    async def log(self, scope: HTTPScope, info: AccessInfo) -> None:
        atoms = AccessLogAtoms(scope, info)

        await self._logger.ainfo(
            "Received Request",
            client_addr=atoms.get("client_addr"),
            method=atoms.get("m"),
            path=atoms.get("U"),
            protocol=atoms.get("H"),
            status=atoms.get("status_code"),
            time=f"{atoms.get('M')}ms",
        )
