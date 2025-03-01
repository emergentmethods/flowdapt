import os

# from datetime import datetime
from collections import defaultdict

import grpc
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GRPCOTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCOTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HTTPOTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPOTLPSpanExporter,
)
from opentelemetry.instrumentation.asgi import (
    OpenTelemetryMiddleware as TelemetryMiddleware,
)
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import (
    MeterProvider,
)
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    MetricExporter,
    MetricExportResult,
    MetricsData,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Span, Status, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from flowdapt import __version__
from flowdapt.lib.config import Configuration
from flowdapt.lib.enum import TelemetryCompression, TelemetryProtocol
from flowdapt.lib.serializers import JSONSerializer


__all__ = (
    "setup_telemetry",
    "shutdown_telemetry",
    "get_tracer",
    "get_current_span",
    "get_meter",
    "TelemetryMiddleware",
    "Status",
    "StatusCode",
)


def setup_telemetry(config: Configuration):
    # Create the resource information for this node
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: config.name,
            ResourceAttributes.SERVICE_VERSION: __version__,
            ResourceAttributes.SERVICE_INSTANCE_ID: os.getpid(),
        }
    )

    trace_exporter: SpanExporter
    metrics_exporter: MetricExporter

    # We always keep some metrics in memory to serve in the Rest API
    # Create the in memory metrics container
    set_metrics_container(
        MetricsContainer(
            # By default we only keep up to 6 hours of metrics
            # This is to prevent the memory from growing out of control
            # however each metric has a differnt length of data points for that
            # period of time.
            max_time_seconds=config.telemetry.metrics_max_storage_time_s,
        )
    )

    # Setup the tracer provider
    if config.telemetry.enabled:
        kwargs = {
            "endpoint": config.telemetry.endpoint,
            "headers": config.telemetry.headers,
            "timeout": config.telemetry.timeout,
        }

        # If enabled we're sending traces and metrics to the collector
        match config.telemetry.protocol:
            case TelemetryProtocol.grpc:
                # Get the compression method
                compression = {
                    TelemetryCompression.gzip: grpc.Compression.Gzip,
                    TelemetryCompression.deflate: grpc.Compression.Deflate,
                    TelemetryCompression.none: grpc.Compression.NoCompression,
                }[config.telemetry.compression]
                trace_exporter = GRPCOTLPSpanExporter(
                    compression=compression,
                    **kwargs,  # type: ignore
                )
                metrics_exporter = GRPCOTLPMetricExporter(
                    compression=compression,
                    **kwargs,  # type: ignore
                )
            case TelemetryProtocol.http:
                # TODO: The HTTP exporter fails to export when compression is passed
                endpoint = kwargs.pop("endpoint")
                trace_exporter = HTTPOTLPSpanExporter(
                    # The collector expects the endpoint to include the full path
                    endpoint=f"{endpoint}/v1/traces",
                    **kwargs,  # type: ignore
                )
                metrics_exporter = HTTPOTLPMetricExporter(
                    # The collector expects the endpoint to include the full path
                    endpoint=f"{endpoint}/v1/metrics",
                    **kwargs,  # type: ignore
                )
    else:
        # If disabled we just dump the traces and metrics to null
        trace_exporter = ConsoleSpanExporter(out=open(os.devnull, "w"))
        metrics_exporter = ConsoleMetricExporter(out=open(os.devnull, "w"))

    # Create the trace and metrics providers
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(
            span_exporter=trace_exporter,
            max_queue_size=config.telemetry.trace_max_queue_size,
            max_export_batch_size=config.telemetry.trace_export_batch_size,
            schedule_delay_millis=config.telemetry.trace_schedule_delay_ms,
            export_timeout_millis=config.telemetry.trace_export_timeout_ms,
        )
    )

    metrics_provider = MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                exporter=metrics_exporter,
                export_interval_millis=config.telemetry.metrics_interval_ms,
                export_timeout_millis=config.telemetry.metrics_export_timeout_ms,
            ),
            PeriodicExportingMetricReader(
                exporter=InMemoryMetricsExporter(),
                export_interval_millis=config.telemetry.metrics_interval_ms,
                export_timeout_millis=config.telemetry.metrics_export_timeout_ms,
            ),
        ],
        resource=resource,
    )

    # Setup the system metrics
    SystemMetricsInstrumentor().instrument()

    # Set the providers as global
    trace.set_tracer_provider(trace_provider)
    metrics.set_meter_provider(metrics_provider)

    # Sometimes a transient error will pop up randomly, see the following issue:
    # https://github.com/open-telemetry/opentelemetry-collector/issues/6363
    # We can just ignore it


def shutdown_telemetry() -> None:
    # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md#retry
    # https://github.com/open-telemetry/opentelemetry-python/issues/3309
    # If the exporters have not been able to connect to the collector
    # then it will be stuck in a loop during shutdown for at least 30 seconds
    # before it finally gets killed.
    metrics.get_meter_provider().shutdown(timeout_millis=1000)  # type: ignore
    trace.get_tracer_provider().shutdown()  # type: ignore


def get_tracer(name: str, version: str = "") -> Tracer:
    """
    Get a tracer with the given name and version.

    :param name: The name of the tracer.
    :type name: str
    :param version: The version of the tracer.
    :type version: str
    :return: A tracer.
    :rtype: Tracer
    """
    return trace.get_tracer(name, version or None)


def get_current_span() -> Span:
    """
    Get the current span.

    :return: The current span.
    :rtype: Span
    """
    return trace.get_current_span()


def get_trace_parent() -> str | None:
    """
    Get the current trace parent ID.
    """
    carrier: dict = {}
    TraceContextTextMapPropagator().inject(carrier)
    return carrier.get("traceparent", None)


def get_trace_id() -> str:
    """
    Get the current formatted trace ID.
    """
    return trace.format_trace_id(get_current_span().get_span_context().trace_id)


def ctx_from_parent(trace_parent: str) -> trace.Context:
    """
    Get a span context from a trace parent ID.
    """
    carrier = {"traceparent": trace_parent}
    return TraceContextTextMapPropagator().extract(carrier)


def get_meter(name: str, version: str = "") -> Meter:
    """
    Get a meter with the given name and version.

    :param name: The name of the meter.
    :type name: str
    :param version: The version of the meter.
    :type version: str
    """
    return metrics.get_meter(name, version)


class MetricsContainer:
    def __init__(self, max_time_seconds: int) -> None:
        """
        :param max_time: The maximum number of seconds to store datapoints for.
        :type max_time: int
        """
        self._max_time_nano = max_time_seconds * 1e9
        self._metrics: defaultdict[str, list] = defaultdict(list)

    def add_data_points(self, metric: str, data_points: list[dict]) -> None:
        """
        Add data points to the container.

        :param metric: The name of the metric to add data points for.
        :type metric: str
        :param data_points: A list of data points to add.
        :type data_points: list
        """
        # Add new data points to the buffer
        self._metrics[metric] = sorted(
            data_points + self._metrics[metric], key=lambda x: x["time_unix_nano"], reverse=True
        )

        # Get the latest time_unix_nano across all data points
        latest_time = max(data_point["time_unix_nano"] for data_point in self._metrics[metric])

        # Remove data points that are older than max_time seconds
        self._metrics[metric] = [
            data_point
            for data_point in self._metrics[metric]
            if latest_time - data_point["time_unix_nano"] <= self._max_time_nano
        ]

    def get_data_points(
        self,
        metric: str,
        start_time: int | None = None,
        end_time: int | None = None,
        max_length: int | None = None,
    ) -> list:
        """
        Get data points for a metric.

        :param metric: The name of the metric to get data points for.
        :type metric: str
        :param start_time: The start time of the data points in unix nano time.
        If None, returns data points from the beginning.
        :type start_time: int, optional
        :param end_time: The end time of the data points in unix nano time.
        If None, returns data points up to the most recent.
        :type end_time: int, optional
        :param max_length: The maximum number of data points to return.
        If None, returns all data points.
        :type max_length: int, optional
        :return: A list of data points.
        :rtype: list
        """
        data_points = self._metrics.get(metric, [])

        if start_time is not None:
            data_points = [
                point for point in data_points if point["start_time_unix_nano"] >= start_time
            ]

        if end_time is not None:
            data_points = [point for point in data_points if point["time_unix_nano"] <= end_time]

        if max_length is not None:
            data_points = data_points[:max_length]

        return data_points

    def get_available_metrics(self) -> list[str]:
        """
        Get a list of available metrics.
        """
        return list(self._metrics.keys())


_container: MetricsContainer | None = None


def set_metrics_container(container: MetricsContainer) -> None:
    global _container
    _container = container


def get_metrics_container() -> MetricsContainer:
    global _container
    if _container is None:
        raise RuntimeError("Metrics container not set")
    return _container


class InMemoryMetricsExporter(MetricExporter):
    """
    A custom metrics exporter to add to the MetricsContainer.
    """

    def export(  # type: ignore
        self, metrics_data: MetricsData, **kwargs
    ) -> MetricExportResult:
        data: dict = JSONSerializer.loads(metrics_data.to_json().encode())

        for resource_metric in data["resource_metrics"]:
            for scope_metric in resource_metric["scope_metrics"]:
                for metric in scope_metric["metrics"]:
                    name = metric["name"]
                    data_points = metric["data"]["data_points"]

                    get_metrics_container().add_data_points(name, data_points)

        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 0.0, **kwargs) -> None:
        pass

    def force_flush(self, timeout_millis: float = 0.0) -> bool:
        return True
