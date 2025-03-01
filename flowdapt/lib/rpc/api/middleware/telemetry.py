from time import process_time_ns

from asgiref.typing import ASGIApplication

from flowdapt.lib.telemetry import TelemetryMiddleware as OpenTelemetryMiddleware
from flowdapt.lib.telemetry import get_meter, get_trace_id


meter = get_meter(__name__)


class TelemetryMiddleware:
    def __init__(self, app: ASGIApplication):
        self._orig = app
        # Add the premade middleware so we can take advantage
        # of what's already there
        self._app = OpenTelemetryMiddleware(self._orig)

        self._requests_counter = meter.create_counter(
            name="api_request_count",
            description="Number of requests",
            unit="1",
        )
        self._requests_size_counter = meter.create_histogram(
            name="api_request_size",
            description="Size of requests",
            unit="bytes",
        )
        self._errors_counter = meter.create_counter(
            name="api_error_count",
            description="Number of errors",
            unit="1",
        )
        self._latency_recorder = meter.create_histogram(
            name="api_request_latency",
            description="Latency of requests",
            unit="ms",
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Call the original middleware
            await self._app(scope, receive, send)
            return

        async def receive_wrapper():
            nonlocal body_size

            message = await receive()
            assert message["type"] == "http.request"

            body_size += len(message.get("body", b""))
            return message

        trace_id = get_trace_id()

        # Increment the requests counter
        self._requests_counter.add(1, {"trace_id": trace_id})

        body_size = 0
        start = process_time_ns()
        # Call the original middleware
        await self._app(scope, receive_wrapper, send)
        # Calculate the latency
        latency = (process_time_ns() - start) / 1e6

        # Record the request size
        self._requests_size_counter.record(body_size, {"trace_id": trace_id})

        # Record the latency
        self._latency_recorder.record(latency, {"trace_id": trace_id})

        # Check if there was an error
        if scope["type"] == "http.response.start":
            if scope["status"] >= 400:
                self._errors_counter.add(1, {"trace_id": trace_id})
