from typing import Any

from flowdapt.lib.utils.model import BaseModel, RootModel


class V1Alpha1MetricsCountValue(BaseModel):
    attributes: dict[str, Any]
    start_time_unix_nano: int
    time_unix_nano: int
    value: float | int


class V1Alpha1MetricsBucketValue(BaseModel):
    attributes: dict[str, Any]
    start_time_unix_nano: int
    time_unix_nano: int
    count: int
    bucket_counts: list[int]
    explicit_bounds: list[float | int]
    sum: float | int
    min: float | int
    max: float | int


class V1Alpha1Metrics(
    RootModel[dict[str, list[V1Alpha1MetricsCountValue | V1Alpha1MetricsBucketValue]]]
):
    @classmethod
    def from_model(cls, model: dict[str, list]):
        return cls(model)
