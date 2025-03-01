from datetime import datetime, timezone

from fastapi import Depends, Response, status

from flowdapt.core.domain.dto import MetricsReadDTOs, MetricsResponse
from flowdapt.lib.domain.dto.protocol import DTOPair
from flowdapt.lib.rpc import RPCRouter
from flowdapt.lib.rpc.api.utils import (
    build_response,
    build_responses_dict,
    get_versioned_dto,
    responses_from_dtos,
)
from flowdapt.lib.telemetry import get_metrics_container


METRICS_RESOURCE_TYPE = "metrics"

router = RPCRouter(tags=["health"])


@router.add_api_route(
    "/metrics",
    method="GET",
    response_model=MetricsResponse,
    summary="Current system metrics",
    response_description="System metrics",
    status_code=status.HTTP_200_OK,
    responses=build_responses_dict(responses_from_dtos(MetricsReadDTOs, METRICS_RESOURCE_TYPE)),
    response_class=Response,
    name="metrics",
)
async def get_metrics(
    name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    max_length: int | None = None,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(MetricsReadDTOs, resource_type=METRICS_RESOURCE_TYPE)
    ),
):
    (_, response_dto), version = versioned_dto

    if start_time:
        start_time_unix_nano = int(start_time.replace(tzinfo=timezone.utc).timestamp() * 1e9)
    else:
        start_time_unix_nano = None

    if end_time:
        end_time_unix_nano = int(end_time.replace(tzinfo=timezone.utc).timestamp() * 1e9)
    else:
        end_time_unix_nano = None

    container = get_metrics_container()

    if name:
        model = {
            name: container.get_data_points(
                metric=name,
                start_time=start_time_unix_nano,
                end_time=end_time_unix_nano,
                max_length=max_length,
            )
        }
    else:
        model = {
            metric: container.get_data_points(
                metric=metric,
                start_time=start_time_unix_nano,
                end_time=end_time_unix_nano,
                max_length=max_length,
            )
            for metric in container.get_available_metrics()
        }

    return build_response(response_dto, model, METRICS_RESOURCE_TYPE, version)
