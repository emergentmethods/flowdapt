from enum import Enum


class TelemetryProtocol(str, Enum):
    grpc = "grpc"
    http = "http"


class TelemetryCompression(str, Enum):
    gzip = "gzip"
    deflate = "deflate"
    none = "none"
