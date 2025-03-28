from __future__ import annotations

from datetime import timedelta
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

from manifest import Instantiable, Manifest
from pydantic import PlainSerializer
from pytimeparse.timeparse import timeparse as parse_duration

from flowdapt.compute.executor.base import Executor
from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.enum import TelemetryCompression, TelemetryProtocol
from flowdapt.lib.utils.asynctools import async_cache
from flowdapt.lib.utils.misc import generate_name
from flowdapt.lib.utils.model import (
    IS_V1,
    BaseModel,
    ConfigDict,
    Field,
    after_validator,
    pre_validator,
)


_CONFIG = None
_APP_DIR: Path | None = None


def set_app_dir(app_dir: Path) -> None:
    """
    Set the application directory.
    """
    global _APP_DIR
    _APP_DIR = app_dir

    _APP_DIR.mkdir(parents=True, exist_ok=True)


def get_app_dir() -> Path | None:
    """
    Get the application directory.
    """
    return _APP_DIR


# ---------------------------- TELEMETRY -------------------------


class TelemetrySettings(BaseModel):
    if not IS_V1:
        model_config = ConfigDict(use_enum_values=True, validate_default=True)
    else:

        class Config:
            use_enum_values = True

    enabled: bool = False
    endpoint: str = "http://localhost:4318"
    protocol: TelemetryProtocol = TelemetryProtocol.http
    compression: TelemetryCompression = TelemetryCompression.none
    timeout: int = 10
    headers: dict | None = None
    trace_export_timeout_ms: int = 30000
    trace_export_batch_size: int = 512
    trace_schedule_delay_ms: int = 5000
    trace_max_queue_size: int = 2048
    metrics_max_storage_time_s: int = 60 * 60 * 6
    metrics_interval_ms: int = 5000
    metrics_export_timeout_ms: int = 10000


# ----------------------------- STORAGE --------------------------


class StorageSettings(BaseModel):
    protocol: str = "file"
    base_path: str = ""
    parameters: dict[str, Any] = {}

    @pre_validator()
    @classmethod
    def _validate(cls, values: dict):
        if values.get("protocol") == "file" and not values.get("base_path"):
            # If not specified, and we're using local disk as the storage
            # protocol then default the base path to the app directory
            if app_dir := get_app_dir():
                values["base_path"] = str(app_dir)
        return values


# ---------------------------- LOGGING ---------------------------


class LoggingSettings(BaseModel):
    level: str = "info"
    format: str = "console"
    include_trace_id: bool = False
    show_tracebacks: bool = False
    traceback_show_locals: bool = False
    traceback_max_frames: int = 10

    @after_validator()
    def _validate(cls, value: LoggingSettings):
        value.level = value.level.upper()
        return value


# ------------------------------ RPC -----------------------------


class EventBusSettings(BaseModel):
    url: str = "memory://"


class RestAPISettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class RPCSettings(BaseModel):
    api: RestAPISettings = RestAPISettings()
    event_bus: EventBusSettings = EventBusSettings()


# ------------------------- DATABASE ------------------------------


class DatabaseSettings(Instantiable[BaseStorage]):
    target: str = Field(
        alias="__target__", default="flowdapt.lib.database.storage.tdb.TinyDBStorage"
    )


# --------------------- SERVICE SETTINGS -----------------------------


class BaseServiceSettings(BaseModel): ...


class ComputeSettings(BaseServiceSettings):
    # Default to LocalExecutor, and allow users to specify either
    # target, params, or both
    class DefaultComputeExecutor(Instantiable[Executor]):
        target: str = Field(
            alias="__target__", default="flowdapt.compute.executor.local.LocalExecutor"
        )

    executor: Instantiable[Executor] = DefaultComputeExecutor()
    default_namespace: str = "default"
    default_os_strategy: Literal["fallback", "artifact", "cluster_memory"] = "fallback"
    run_retention_duration: Annotated[
        timedelta | int | str,
        PlainSerializer(
            lambda v: str(v) if v != -1 else v, return_type=str | int, when_used="always"
        ),
    ] = -1

    @pre_validator()
    def _validate(cls, values: Any):
        run_retention_duration = values.get("run_retention_duration")

        if isinstance(run_retention_duration, str):
            seconds = parse_duration(run_retention_duration)

            if not seconds:
                raise ValueError(
                    f"Invalid duration '{run_retention_duration}' for run_retention_duration"
                )

            values["run_retention_duration"] = timedelta(seconds=seconds)
        elif isinstance(run_retention_duration, int) and not run_retention_duration <= 0:
            values["run_retention_duration"] = timedelta(seconds=run_retention_duration)
        elif isinstance(run_retention_duration, int) and run_retention_duration < 0:
            values["run_retention_duration"] = -1

        return values


class ServiceSettings(BaseModel):
    compute: ComputeSettings | Literal["disabled"] = ComputeSettings()


# ---------------------- MAIN MODEL --------------------------------


class Configuration(Manifest):
    config_file: Path | None = Field(None, exclude=True)
    dev_mode: bool = Field(False, exclude=True)

    name: str = Field(default_factory=lambda: f"flowdapt.{generate_name()}")

    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    rpc: RPCSettings = Field(default_factory=RPCSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    services: ServiceSettings = Field(default_factory=ServiceSettings)


@cache
def get_temp_config() -> Configuration:
    return Configuration()


@async_cache
async def config_from_env(
    dotenv_files: list[str] = [], env_prefix: str = "FLOWDAPT", **kwargs
) -> Configuration:
    return await Configuration.from_env(dotenv_files=dotenv_files, env_prefix=env_prefix, **kwargs)


def set_configuration(config: Configuration):
    global _CONFIG
    _CONFIG = config


def get_configuration(use_temp: bool = True) -> Configuration:
    global _CONFIG

    if not _CONFIG and use_temp:
        return get_temp_config()

    return _CONFIG
