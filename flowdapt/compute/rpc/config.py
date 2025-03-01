from fastapi import Depends, Request, Response, status

from flowdapt.compute.domain.dto import (
    ConfigResourceCreateDTOs,
    ConfigResourceCreateResponse,
    ConfigResourceReadDTOs,
    ConfigResourceReadResponse,
    ConfigResourceUpdateDTOs,
    ConfigResourceUpdateResponse,
)
from flowdapt.compute.domain.models.config import CONFIG_RESOURCE_KIND
from flowdapt.compute.resources.config.methods import (
    create_config,
    delete_config,
    get_config,
    list_configs,
    update_config,
)
from flowdapt.lib.domain.dto.protocol import DTOPair
from flowdapt.lib.domain.dto.utils import to_model
from flowdapt.lib.errors import APIErrorModel
from flowdapt.lib.rpc import RPCRouter
from flowdapt.lib.rpc.api.utils import (
    build_response,
    build_responses_dict,
    get_versioned_dto,
    parse_request_body,
    requests_from_dtos,
    responses_from_dtos,
)


router = RPCRouter(prefix="/configs", tags=["configs"])


# API GET @ /api/configs/
@router.add_api_route(
    "/",
    method="GET",
    response_model=list[ConfigResourceReadResponse],
    summary="List all Configs",
    response_description="List of Configs",
    responses=build_responses_dict(
        responses_from_dtos(ConfigResourceReadDTOs, CONFIG_RESOURCE_KIND, is_array=True),
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="list_configs",
)
async def list_configs_api(
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(ConfigResourceReadDTOs, resource_type=CONFIG_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    models = await list_configs()
    return build_response(response_dto, models, CONFIG_RESOURCE_KIND, version, recursive=True)


# API POST @ /api/configs/
@router.add_api_route(
    "/",
    method="POST",
    response_model=ConfigResourceCreateResponse,
    summary="Create a Config",
    response_description="Created Config",
    responses=build_responses_dict(
        responses_from_dtos(ConfigResourceCreateDTOs, CONFIG_RESOURCE_KIND, ok_status=201),
    ),
    response_class=Response,
    openapi_extra={
        "requestBody": {**requests_from_dtos(ConfigResourceCreateDTOs, CONFIG_RESOURCE_KIND)}
    },
    status_code=status.HTTP_201_CREATED,
    name="create_config",
)
async def create_config_api(
    request: Request,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(ConfigResourceCreateDTOs, resource_type=CONFIG_RESOURCE_KIND)
    ),
):
    (request_dto, response_dto), version = versioned_dto
    payload = await parse_request_body(request, request_dto)
    model = await create_config(to_model(payload))
    return build_response(response_dto, model, CONFIG_RESOURCE_KIND, version)


# API GET @ /api/configs/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="GET",
    response_model=ConfigResourceReadResponse,
    summary="Get a Config",
    response_description="Config",
    responses=build_responses_dict(
        {
            **responses_from_dtos(ConfigResourceReadDTOs, CONFIG_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="get_config",
)
async def get_config_api(
    identifier: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(ConfigResourceReadDTOs, resource_type=CONFIG_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await get_config(identifier)
    return build_response(response_dto, model, CONFIG_RESOURCE_KIND, version)


# API DELETE @ /api/configs/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="DELETE",
    response_model=ConfigResourceReadResponse,
    summary="Delete a Config",
    response_description="Deleted Config",
    responses=build_responses_dict(
        responses_from_dtos(ConfigResourceReadDTOs, CONFIG_RESOURCE_KIND),
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="delete_config",
)
async def delete_config_api(
    identifier: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(ConfigResourceReadDTOs, resource_type=CONFIG_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await delete_config(identifier)
    return build_response(response_dto, model, CONFIG_RESOURCE_KIND, version)


# API PUT @ /api/configs/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="PUT",
    response_model=ConfigResourceUpdateResponse,
    summary="Update a Config",
    response_description="Updated Config",
    responses=build_responses_dict(
        responses_from_dtos(ConfigResourceUpdateDTOs, CONFIG_RESOURCE_KIND),
    ),
    response_class=Response,
    openapi_extra={
        "requestBody": {**requests_from_dtos(ConfigResourceUpdateDTOs, CONFIG_RESOURCE_KIND)}
    },
    status_code=status.HTTP_200_OK,
    name="update_config",
)
async def update_config_api(
    identifier: str,
    request: Request,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(ConfigResourceUpdateDTOs, resource_type=CONFIG_RESOURCE_KIND)
    ),
):
    (request_dto, response_dto), version = versioned_dto
    parsed_request = await parse_request_body(request, request_dto)
    model = to_model(parsed_request)
    model = await update_config(identifier, model)
    return build_response(response_dto, model, CONFIG_RESOURCE_KIND, version)
