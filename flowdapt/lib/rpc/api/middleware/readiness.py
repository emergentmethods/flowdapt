from asgiref.typing import ASGIApplication
from fastapi.responses import JSONResponse

from flowdapt.lib.context import get_context


class ServiceReadyMiddleware:
    def __init__(self, app: ASGIApplication):
        self._app = app
        self._context = get_context()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":  # Only apply this middleware for http requests
            if not self._context.flags["services_ready"]:
                # If the services aren't ready, return a 503 Service Unavailable response.
                response = JSONResponse({"detail": "Service not available"}, status_code=503)
                await response(scope, receive, send)
            else:
                await self._app(scope, receive, send)
        else:
            await self._app(scope, receive, send)
