from fastapi import Depends, Response, status

from flowdapt.core.domain.dto import SystemStatusReadDTOs, SystemStatusResponse
from flowdapt.core.domain.models.status import SYSTEM_STATUS_RESOURCE_KIND, SystemStatus
from flowdapt.lib.domain.dto.protocol import DTOPair
from flowdapt.lib.rpc import RPCRouter
from flowdapt.lib.rpc.api.utils import (
    build_response,
    build_responses_dict,
    get_versioned_dto,
    responses_from_dtos,
)


router = RPCRouter(tags=["health"])


@router.add_api_route(
    "/status",
    method="GET",
    response_model=SystemStatusResponse,
    summary="Current system information",
    response_description="System info",
    status_code=status.HTTP_200_OK,
    responses=build_responses_dict(
        responses_from_dtos(SystemStatusReadDTOs, SYSTEM_STATUS_RESOURCE_KIND),
    ),
    response_class=Response,
    name="status",
)
async def get_status_api(
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(SystemStatusReadDTOs, resource_type=SYSTEM_STATUS_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    return build_response(
        response_dto, await SystemStatus.snapshot(), SYSTEM_STATUS_RESOURCE_KIND, version
    )
