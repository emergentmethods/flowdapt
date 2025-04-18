import logging
import sys
import time
from contextlib import contextmanager
from io import StringIO
from types import TracebackType
from typing import IO, Callable, Iterator, Optional, Type, TypeAlias

import structlog
from rich.console import Console
from rich.traceback import Traceback
from structlog._log_levels import NAME_TO_LEVEL
from structlog.processors import ExceptionDictTransformer, ExceptionRenderer
from structlog.testing import capture_logs
from structlog.typing import EventDict, Processor

from flowdapt.lib.utils.misc import hash_map
from flowdapt.lib.utils.model import model_dump


LoggerType: TypeAlias = structlog.stdlib.BoundLogger
ExcInfo = tuple[Type[BaseException], BaseException, Optional[TracebackType]]

_COLORS = {
    "DEBUG": "blue",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red",
    "TIMESTAMP": "grey70",
    "LOGGER_NAME": "royal_blue1",
    "KEY": "grey70",
    "VALUE": "sky_blue3",
}

_last_log_times: dict[int, float] = {}


def _get_color(name: str) -> str:
    return _COLORS.get(name.upper(), "white")


def log_once(log_method: Callable, event: str, interval_seconds=60, **kwargs):
    key = hash_map({"event": event, **kwargs})
    last_time = _last_log_times.get(key, 0)
    current_time = time.time()

    if current_time - last_time >= interval_seconds:
        _last_log_times[key] = current_time
        return log_method(event, **kwargs)
    else:
        return None


def inject_trace_id(logger: LoggerType, method_name: str, event_dict: EventDict) -> dict:
    from flowdapt.lib.telemetry import get_trace_id

    if not event_dict.get("trace_id"):
        event_dict["trace_id"] = get_trace_id()
    return event_dict


def rich_traceback(
    sio: IO,
    exc_info: ExcInfo,
    show_locals: bool = False,
    max_frames: int = 10,
) -> None:
    sio.write("\n")

    Console(file=sio, color_system="truecolor").print(
        Traceback.from_exception(
            *exc_info,
            show_locals=show_locals,
            max_frames=max_frames,
        )
    )


class RichPrintLogger:
    def __init__(self, file: IO | None = None):
        self.file = file or sys.stderr
        self.console = Console(width=255)

    def msg(self, message: str):
        self.console.print(message, highlight=False, markup=True)

    info = debug = info = warn = warning = error = exception = critical = msg
    fatal = failure = criticial = exception = msg


class RichPrintLoggerFactory:
    def __init__(self, file: IO | None = None):
        self.file = file or sys.stdout

    def __call__(self, *args, **kwargs) -> RichPrintLogger:
        return RichPrintLogger(file=self.file)


class ConsoleRenderer:
    def __init__(
        self,
        show_tracebacks: bool = True,
        traceback_show_locals: bool = False,
        traceback_max_frames: int = 10,
        exception_transformer: structlog.typing.ExceptionRenderer = rich_traceback,
    ):
        self._show_tracebacks = show_tracebacks
        self._traceback_show_locals = traceback_show_locals
        self._traceback_max_frames = traceback_max_frames
        self._exc_transformer = exception_transformer

    def __call__(self, logger: structlog.typing.WrappedLogger, name: str, event_dict: EventDict) -> str:
        output = ""

        timestamp = event_dict.pop("timestamp", None)
        logger_name = event_dict.pop("logger_name", None)
        level = event_dict.pop("level", None)
        event = event_dict.pop("event", None)
        exc_info = event_dict.pop("exc_info", None)

        rendered_kw = []

        if timestamp:
            output += f"\\[[{_get_color('timestamp')}]{timestamp}[/{_get_color('timestamp')}]]"

        if level:
            output += f"\\[[{_get_color(level)}]{level}[/{_get_color(level)}]]"

        if logger_name:
            output += (
                f"\\[[{_get_color('logger_name')}]{logger_name}[/{_get_color('logger_name')}]]"  # noqa: E501
            )

        rendered_kw.append(
            f"[{_get_color('key')}]event[/{_get_color('key')}]=[{_get_color('value')}]{event}[/{_get_color('value')}]"
        )  # noqa: E501
        rendered_kw.extend(
            [
                f"[{_get_color('key')}]{k}[/{_get_color('key')}]=[{_get_color('value')}]{v}[/{_get_color('value')}]"  # noqa: E501
                for k, v in event_dict.items()
            ]
        )

        output += f"\\[{' '.join(rendered_kw)}]"

        if exc_info and self._show_tracebacks:
            exc_output = StringIO()
            self._exc_transformer(
                exc_output,
                exc_info,
                show_locals=self._traceback_show_locals,
                max_frames=self._traceback_max_frames,
            )

            output += exc_output.getvalue()

        return output


def get_logger(name: str, **kwargs) -> LoggerType:
    return structlog.get_logger(logger_name=name, **kwargs)


def get_logging_level(level: str) -> int:
    """
    Get the logging level from a string.

    :param level: The logging level.
    :type level: str
    :return: The logging level.
    :rtype: int
    """
    return NAME_TO_LEVEL.get(level.lower(), logging.INFO)


def configure_logger(
    level: str = "INFO",
    format: str = "console",
    include_trace_id: bool = False,
    show_tracebacks: bool = True,
    traceback_show_locals: bool = False,
    traceback_max_frames: int = 10,
):
    print("LOGGING LEVEL:", level)
    output_processors: list[Processor]
    shared_processors: list[Processor] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
    ]

    if include_trace_id:
        shared_processors.append(inject_trace_id)

    match format:
        case "console":
            output_processors = [
                ConsoleRenderer(
                    show_tracebacks=show_tracebacks,
                    traceback_show_locals=traceback_show_locals,
                    traceback_max_frames=traceback_max_frames,
                ),
            ]
        case "json":
            output_processors = [
                ExceptionRenderer(
                    ExceptionDictTransformer(
                        show_locals=traceback_show_locals,
                        locals_max_string=100,
                        max_frames=traceback_max_frames,
                    )
                ),
                structlog.processors.JSONRenderer(),
            ]
        case _:
            raise ValueError(f"Unknown logging format: {format}")

    structlog.configure(
        logger_factory=RichPrintLoggerFactory(),
        processors=shared_processors + output_processors,
        context_class=dict,
        wrapper_class=structlog.make_filtering_bound_logger(
            get_logging_level(level)
        ),
        cache_logger_on_first_use=False,
    )


def get_logging_configuration() -> dict:
    from flowdapt.lib.config import get_configuration

    return model_dump(get_configuration().logging)


def setup_logging() -> None:
    configure_logger(**get_logging_configuration())


@contextmanager
def disable_logging() -> Iterator[None]:
    with capture_logs():
        yield
