import asyncio
import warnings
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import ORJSONResponse
from typing_extensions import TypedDict
from uvicorn import Config as UvicornConfig
from uvicorn.server import Server as UvicornServer

from flowdapt import __version__
from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc.api.utils import (
    generate_custom_openapi_operation_id,
    openapi_generator,
    use_route_names_as_operation_ids,
)
from flowdapt.lib.rpc.version import __api_version__


logger = get_logger(__name__)


# Monkey patch Uvicorn since we handle signals
class NoSignalServer(UvicornServer):
    def install_signal_handlers(_):
        return None


class APIServer:
    """
    An API Server using FastAPI
    """

    def __init__(
        self, host: str = "127.0.0.1", port: int = 8080, *args, servers: list[dict] = [], **kwargs
    ):
        assert asyncio.get_running_loop(), "APIServer must be instantiated with an active loop"

        self.host = host
        self.port = port
        self.url = f"http://{self.host}:{self.port}/api"
        self._servers = servers or [{"url": self.url}]

        self._application: FastAPI
        self._create_application()

    async def _api_startup_event(self) -> None:
        await logger.ainfo("APIServerStarted", host=self.host, port=self.port)

    async def _api_shutdown_event(self) -> None:
        await logger.ainfo("APIServerStopped")

    def _create_application(self, **kwargs):
        # Disable duplicate operation ID warnings
        warnings.filterwarnings(
            action="ignore",
            message=".*Duplicate Operation ID.*",
        )

        self._application = FastAPI(
            generate_unique_id_function=generate_custom_openapi_operation_id,
            # Disable separating input/output schemas with Pydantic V2
            # We will want to do this at some point but will change the
            # generated sdks so we need to do it all at once.
            # separate_input_output_schemas=False,
            default_response_class=ORJSONResponse,
        )

        self._application.openapi = openapi_generator(
            self._application,
            title="Flowdapt",
            version=__api_version__,
            description="An ML Workflow Orchestration server.",
        )

        @self._application.get(
            "/",
            name="ping",
            response_model=TypedDict(
                "PingResponse", {"app": str, "version": str, "api_version": str}
            ),
        )
        async def ping():
            return {"app": "flowdapt", "version": __version__, "api_version": __api_version__}

        use_route_names_as_operation_ids(self._application)

        self._setup_middlewares(**kwargs)
        self._setup_exception_handlers()

        # https://github.com/tiangolo/fastapi/issues/617
        self._application.add_event_handler(event_type="startup", func=self._api_startup_event)
        self._application.add_event_handler(event_type="shutdown", func=self._api_shutdown_event)

        # Prevent FastAPI from adding the root path to the servers in OpenAPI spec
        self._application.root_path_in_servers = False

    def _setup_middlewares(
        self,
        cors_settings: dict[str, Any] = {},
    ) -> None:
        from fastapi.middleware.cors import CORSMiddleware

        from flowdapt.lib.rpc.api.middleware.logging import AccessLoggerMiddleware
        from flowdapt.lib.rpc.api.middleware.readiness import ServiceReadyMiddleware
        from flowdapt.lib.rpc.api.middleware.telemetry import TelemetryMiddleware

        # ServiceReadyMiddleware must be the first to ensure it's the first one
        # handling requests so we aren't doing anything we don't need to until the Services
        # are ready.
        self._application.add_middleware(ServiceReadyMiddleware)

        # CORS is required for the dashboard, but can be disabled by removing origins.
        # By default we just allow localhost
        self._application.add_middleware(
            CORSMiddleware,
            allow_origins=cors_settings.get(
                "allow_origins", ["http://localhost:3030", "http://127.0.0.1:3030"]
            ),
            allow_origin_regex=cors_settings.get(
                "allow_origin_regex", r"http://localhost:\d+|http://127.0.0.1:\d+"
            ),
            allow_credentials=cors_settings.get("allow_credentials", True),
            allow_methods=cors_settings.get("allow_methods", ["*"]),
            allow_headers=cors_settings.get("allow_headers", ["*"]),
        )

        # Add access logs
        self._application.add_middleware(
            AccessLoggerMiddleware,
            logger=logger,
        )

        # Add tracing
        self._application.add_middleware(TelemetryMiddleware)

    def _setup_exception_handlers(self) -> None:
        from fastapi.exceptions import RequestValidationError

        from flowdapt.lib.rpc.api.exception_handlers import HTTPErrorHandler, ValueErrorHandler

        self._application.exception_handlers = {
            ValueError: ValueErrorHandler,
            RequestValidationError: HTTPErrorHandler,
            HTTPException: HTTPErrorHandler,
            Exception: HTTPErrorHandler,
        }

    def add_router(self, router: APIRouter) -> None:
        """
        Include an APIRouter in the ASGIApplication.

        :param router: The API Router to add
        """
        self._application.include_router(router)

    def generate_spec(self, version: str = "3.0.2"):
        """
        Generate the OpenAPI spec for the application.
        """
        return self._application.openapi(openapi_version=version)

    async def serve(self):
        self.server_config = UvicornConfig(
            self._application,
            host=self.host,
            port=self.port,
            log_level="error",
            access_log=False,
            lifespan="on",
            loop="none",
            headers=[("server", f"flowdapt-{__version__}-uvicorn")],
        )
        self.server = NoSignalServer(self.server_config)

        try:
            await self.server.serve()
        except Exception as e:
            await logger.aexception("APIServerExceptionOccurred", error=str(e))

    async def stop(self):
        self.server.should_exit = True
