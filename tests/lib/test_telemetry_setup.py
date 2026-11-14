from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from flowdapt.lib import telemetry
from flowdapt.lib.config import Configuration


@pytest.fixture
def otel(monkeypatch):
    """
    Replace everything `setup_telemetry` would build or register globally, so
    the tests can see what it does without leaving real providers (which can
    only be set once per process) or export threads behind.
    """
    names = [
        "TracerProvider",
        "MeterProvider",
        "BatchSpanProcessor",
        "PeriodicExportingMetricReader",
        "SystemMetricsInstrumentor",
        "HTTPOTLPSpanExporter",
        "HTTPOTLPMetricExporter",
    ]
    mocks = {name: MagicMock(name=name) for name in names}
    for name, mock in mocks.items():
        monkeypatch.setattr(telemetry, name, mock)

    mocks["set_tracer_provider"] = MagicMock(name="set_tracer_provider")
    mocks["set_meter_provider"] = MagicMock(name="set_meter_provider")
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", mocks["set_tracer_provider"])
    monkeypatch.setattr(telemetry.metrics, "set_meter_provider", mocks["set_meter_provider"])

    yield SimpleNamespace(**mocks)

    # Drop the references to the mocked providers
    telemetry.shutdown_telemetry()


def test_disabled_telemetry_collects_no_metrics(otel):
    config = Configuration()
    assert config.telemetry.enabled is False

    telemetry.setup_telemetry(config)

    # No meter provider means every meter in the app is a no-op: nothing is
    # aggregated, the system metrics are not sampled, no reader threads run.
    otel.MeterProvider.assert_not_called()
    otel.set_meter_provider.assert_not_called()
    otel.PeriodicExportingMetricReader.assert_not_called()
    otel.SystemMetricsInstrumentor.assert_not_called()

    # Spans keep their trace ids for the logs, but are not exported anywhere
    otel.set_tracer_provider.assert_called_once_with(otel.TracerProvider.return_value)
    otel.TracerProvider.return_value.add_span_processor.assert_not_called()
    otel.BatchSpanProcessor.assert_not_called()

    # The Rest API can still read the (empty) container
    assert telemetry.get_metrics_container().get_available_metrics() == []


def test_disabled_telemetry_shuts_down_cleanly(otel):
    telemetry.setup_telemetry(Configuration())

    # There is no meter provider to shut down, this must not raise
    telemetry.shutdown_telemetry()

    otel.TracerProvider.return_value.shutdown.assert_called_once_with()


def test_enabled_telemetry_exports_and_keeps_in_memory_metrics(otel):
    config = Configuration()
    config.telemetry.enabled = True

    telemetry.setup_telemetry(config)

    # One reader for the collector, one for the in-memory Rest API metrics
    exporters = [
        call.kwargs["exporter"] for call in otel.PeriodicExportingMetricReader.call_args_list
    ]
    assert len(exporters) == 2
    assert exporters[0] is otel.HTTPOTLPMetricExporter.return_value
    assert isinstance(exporters[1], telemetry.InMemoryMetricsExporter)

    otel.SystemMetricsInstrumentor.return_value.instrument.assert_called_once_with()
    otel.set_meter_provider.assert_called_once_with(otel.MeterProvider.return_value)

    otel.BatchSpanProcessor.assert_called_once()
    assert (
        otel.BatchSpanProcessor.call_args.kwargs["span_exporter"]
        is otel.HTTPOTLPSpanExporter.return_value
    )
    otel.TracerProvider.return_value.add_span_processor.assert_called_once_with(
        otel.BatchSpanProcessor.return_value
    )
    otel.set_tracer_provider.assert_called_once_with(otel.TracerProvider.return_value)

    telemetry.shutdown_telemetry()

    otel.MeterProvider.return_value.shutdown.assert_called_once_with(timeout_millis=1000)
    otel.TracerProvider.return_value.shutdown.assert_called_once_with()
