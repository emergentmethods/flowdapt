from uuid import UUID

from fastapi import Depends, Request, Response, status

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
from flowdapt.lib.rpc.eventbus import Event
from flowdapt.lib.utils.model import model_dump
from flowdapt.triggers.domain.dto import (
    TriggerRuleCreateDTOs,
    TriggerRuleReadDTOs,
    TriggerRuleResourceCreateResponse,
    TriggerRuleResourceReadResponse,
    TriggerRuleResourceUpdateResponse,
    TriggerRuleUpdateDTOs,
)
from flowdapt.triggers.domain.models.triggerrule import (
    TRIGGER_RESOURCE_KIND,
    TriggerRuleResource,
    TriggerRuleType,
)
from flowdapt.triggers.resources.triggers.methods import (
    create_trigger,
    delete_trigger,
    get_trigger,
    list_triggers,
    set_last_run,
    update_trigger,
)
from flowdapt.triggers.service import logger


router = RPCRouter(prefix="/triggers", tags=["triggers"])


# API GET @ /api/triggers/
@router.add_api_route(
    "/",
    method="GET",
    response_model=list[TriggerRuleResourceReadResponse],
    summary="List all Trigger Rules",
    response_description="List of Trigger Rules",
    responses=build_responses_dict(
        responses_from_dtos(TriggerRuleReadDTOs, TRIGGER_RESOURCE_KIND, is_array=True),
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="list_triggers",
)
async def list_triggers_api(
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(TriggerRuleReadDTOs, resource_type=TRIGGER_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    models = await list_triggers()
    return build_response(response_dto, models, TRIGGER_RESOURCE_KIND, version, recursive=True)


# API POST @ /api/triggers/
@router.add_api_route(
    "/",
    method="POST",
    response_model=TriggerRuleResourceCreateResponse,
    summary="Create a new Trigger Rule",
    response_description="The created Trigger Rule",
    responses=build_responses_dict(
        responses_from_dtos(TriggerRuleCreateDTOs, TRIGGER_RESOURCE_KIND),
    ),
    response_class=Response,
    openapi_extra={
        "requestBody": {**requests_from_dtos(TriggerRuleCreateDTOs, TRIGGER_RESOURCE_KIND)}
    },
    status_code=status.HTTP_200_OK,
    name="create_trigger",
)
async def create_trigger_api(
    request: Request,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(TriggerRuleCreateDTOs, resource_type=TRIGGER_RESOURCE_KIND)
    ),
):
    (request_dto, response_dto), version = versioned_dto
    parsed_request = await parse_request_body(request, request_dto)
    model = await create_trigger(to_model(parsed_request))
    return build_response(response_dto, model, TRIGGER_RESOURCE_KIND, version)


# API GET @ /api/triggers/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="GET",
    response_model=TriggerRuleResourceReadResponse,
    summary="Get a Trigger Rule",
    response_description="The Trigger Rule",
    responses=build_responses_dict(
        {
            **responses_from_dtos(TriggerRuleReadDTOs, TRIGGER_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="get_trigger",
)
async def get_trigger_api(
    identifier: str | UUID,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(TriggerRuleReadDTOs, resource_type=TRIGGER_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await get_trigger(identifier)
    return build_response(response_dto, model, TRIGGER_RESOURCE_KIND, version)


# API DELETE @ /api/triggers/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="DELETE",
    response_model=TriggerRuleResourceReadResponse,
    summary="Delete a Trigger Rule",
    response_description="The deleted Trigger Rule",
    responses=build_responses_dict(
        {
            **responses_from_dtos(TriggerRuleReadDTOs, TRIGGER_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="delete_trigger",
)
async def delete_trigger_api(
    identifier: str | UUID,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(TriggerRuleReadDTOs, resource_type=TRIGGER_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await delete_trigger(identifier)
    return build_response(response_dto, model, TRIGGER_RESOURCE_KIND, version)


# API PUT @ /api/v1/triggers/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="PUT",
    response_model=TriggerRuleResourceUpdateResponse,
    summary="Update a Trigger Rule",
    response_description="The updated Trigger Rule",
    responses=build_responses_dict(
        {
            **responses_from_dtos(TriggerRuleUpdateDTOs, TRIGGER_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    openapi_extra={
        "requestBody": {**requests_from_dtos(TriggerRuleUpdateDTOs, TRIGGER_RESOURCE_KIND)}
    },
    status_code=status.HTTP_200_OK,
    name="update_trigger",
)
async def update_trigger_api(
    identifier: str,
    request: Request,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(TriggerRuleUpdateDTOs, resource_type=TRIGGER_RESOURCE_KIND)
    ),
):
    (request_dto, response_dto), version = versioned_dto
    parsed_request = await parse_request_body(request, request_dto)
    model = to_model(parsed_request)
    model = await update_trigger(identifier, model)
    return build_response(response_dto, model, TRIGGER_RESOURCE_KIND, version)


# Event @ $ALL/$ALL
@router.add_event_callback(all=True)
async def handle_all_events_callback(event: Event):
    triggers: list[TriggerRuleResource] = await list_triggers(type=TriggerRuleType.condition)
    for trigger in triggers:
        if trigger.spec.check_condition(model_dump(event)):
            await logger.ainfo(
                "ValidTriggerCondition",
                trigger=trigger.metadata.name,
                event_type=event.type,
                event_source=event.source,
            )
            await set_last_run(trigger)
            await trigger.spec.action.run()
