from fastapi import Body, Depends, Request, Response, status

from flowdapt.compute.domain.dto import (
    WorkflowResourceCreateDTOs,
    WorkflowResourceCreateResponse,
    WorkflowResourceReadDTOs,
    WorkflowResourceReadResponse,
    WorkflowResourceUpdateDTOs,
    WorkflowResourceUpdateResponse,
    WorkflowRunReadDTOs,
    WorkflowRunReadResponse,
)
from flowdapt.compute.domain.events.workflow import RunWorkflowEvent
from flowdapt.compute.domain.models.workflow import WORKFLOW_RESOURCE_KIND
from flowdapt.compute.domain.models.workflowrun import WORKFLOW_RUN_RESOURCE_KIND
from flowdapt.compute.resources.workflow.methods import (
    create_workflow,
    delete_workflow,
    delete_workflow_run,
    get_recent_workflow_runs,
    get_workflow,
    get_workflow_run,
    list_workflows,
    run_workflow,
    update_workflow,
)
from flowdapt.compute.service import logger
from flowdapt.lib.context import inject_context
from flowdapt.lib.domain.dto.protocol import DTOPair
from flowdapt.lib.domain.dto.utils import to_model
from flowdapt.lib.errors import APIErrorModel, ResourceNotFoundError
from flowdapt.lib.rpc import RPC, RPCRouter
from flowdapt.lib.rpc.api.utils import (
    build_response,
    build_responses_dict,
    get_versioned_dto,
    parse_request_body,
    requests_from_dtos,
    responses_from_dtos,
)


router = RPCRouter(prefix="/workflows", tags=["workflows"])


# API GET @ /api/workflows/
@router.add_api_route(
    "/",
    method="GET",
    response_model=list[WorkflowResourceReadResponse],
    summary="List all Workflows",
    response_description="List of Workflows",
    responses=build_responses_dict(
        responses_from_dtos(WorkflowResourceReadDTOs, WORKFLOW_RESOURCE_KIND, is_array=True),
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="list_workflows",
)
async def list_workflows_api(
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(
            WorkflowResourceReadDTOs,
            resource_type=WORKFLOW_RESOURCE_KIND,
        )
    ),
):
    (_, response_dto), version = versioned_dto
    models = await list_workflows()
    return build_response(response_dto, models, WORKFLOW_RESOURCE_KIND, version, recursive=True)


# API GET @ /api/workflows/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="GET",
    response_model=WorkflowResourceReadResponse,
    summary="Get a Workflow",
    response_description="The Workflow Definition",
    responses=build_responses_dict(
        {
            **responses_from_dtos(WorkflowResourceReadDTOs, WORKFLOW_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="get_workflow",
)
async def get_workflow_api(
    identifier: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowResourceReadDTOs, resource_type=WORKFLOW_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await get_workflow(identifier)
    return build_response(response_dto, model, WORKFLOW_RESOURCE_KIND, version)


# API POST @ /api/workflows/
@router.add_api_route(
    "/",
    method="POST",
    response_model=WorkflowResourceCreateResponse,
    summary="Create a Workflow",
    response_description="The created Workflow",
    responses=build_responses_dict(
        responses_from_dtos(WorkflowResourceCreateDTOs, WORKFLOW_RESOURCE_KIND),
    ),
    response_class=Response,
    openapi_extra={
        "requestBody": {**requests_from_dtos(WorkflowResourceCreateDTOs, WORKFLOW_RESOURCE_KIND)}
    },
    status_code=status.HTTP_200_OK,
    name="create_workflow",
)
async def create_workflow_api(
    request: Request,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowResourceCreateDTOs, resource_type=WORKFLOW_RESOURCE_KIND)
    ),
):
    (request_dto, response_dto), version = versioned_dto
    parsed_request = await parse_request_body(request, request_dto)
    model = await create_workflow(to_model(parsed_request))
    return build_response(response_dto, model, WORKFLOW_RESOURCE_KIND, version)


# API DELETE @ /api/workflows/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="DELETE",
    response_model=WorkflowResourceReadResponse,
    summary="Delete Workflow",
    response_description="The Workflow that was deleted",
    responses=build_responses_dict(
        {
            **responses_from_dtos(WorkflowResourceReadDTOs, WORKFLOW_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="delete_workflow",
)
async def delete_workflow_api(
    identifier: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowResourceReadDTOs, resource_type=WORKFLOW_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await delete_workflow(identifier)
    return build_response(response_dto, model, WORKFLOW_RESOURCE_KIND, version)


# API PUT @ /api/workflows/{identifier}
@router.add_api_route(
    "/{identifier}",
    method="PUT",
    response_model=WorkflowResourceUpdateResponse,
    summary="Update a Workflow",
    response_description="The updated Workflow",
    responses=build_responses_dict(
        responses_from_dtos(WorkflowResourceUpdateDTOs, WORKFLOW_RESOURCE_KIND),
    ),
    response_class=Response,
    openapi_extra={
        "requestBody": {**requests_from_dtos(WorkflowResourceUpdateDTOs, WORKFLOW_RESOURCE_KIND)}
    },
    status_code=status.HTTP_200_OK,
    name="update_workflow",
)
async def update_workflow_api(
    identifier: str,
    request: Request,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowResourceUpdateDTOs, resource_type=WORKFLOW_RESOURCE_KIND)
    ),
):
    (request_dto, response_dto), version = versioned_dto
    parsed_request = await parse_request_body(request, request_dto)
    model = to_model(parsed_request)
    model = await update_workflow(identifier, model)
    return build_response(response_dto, model, WORKFLOW_RESOURCE_KIND, version)


# API POST @ /api/workflows/{identifier}/run
@router.add_api_route(
    "/{identifier}/run",
    method="POST",
    response_model=WorkflowRunReadResponse,
    summary="Run a Workflow",
    response_description="The WorkflowRun that was created",
    responses=build_responses_dict(
        {
            **responses_from_dtos(WorkflowRunReadDTOs, WORKFLOW_RUN_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="run_workflow",
)
async def run_workflow_api(
    identifier: str,
    namespace: str | None = None,
    payload: dict = Body({}),
    wait: bool = True,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowRunReadDTOs, resource_type=WORKFLOW_RUN_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await run_workflow(
        identifier=identifier, input=payload, wait=wait, namespace=namespace, source="api"
    )
    return build_response(response_dto, model, WORKFLOW_RUN_RESOURCE_KIND, version)


# API GET @ /api/workflows/{identifier}/run
@router.add_api_route(
    "/{identifier}/run",
    method="GET",
    response_model=list[WorkflowRunReadResponse],
    summary="List Workflow Runs",
    response_description="List of Workflow Runs",
    responses=build_responses_dict(
        responses_from_dtos(WorkflowRunReadDTOs, WORKFLOW_RUN_RESOURCE_KIND, is_array=True),
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="list_workflow_runs",
)
async def list_workflow_runs_api(
    identifier: str,
    limit: int = 10,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(
            WorkflowRunReadDTOs,
            resource_type=WORKFLOW_RUN_RESOURCE_KIND,
        )
    ),
):
    (_, response_dto), version = versioned_dto
    models = await get_recent_workflow_runs(workflow=identifier, limit=limit)
    return build_response(response_dto, models, WORKFLOW_RUN_RESOURCE_KIND, version, recursive=True)


# API GET @ /api/workflows/run/{identifier}
@router.add_api_route(
    "/run/{identifier}",
    method="GET",
    response_model=WorkflowRunReadResponse,
    summary="Get a Workflow Run",
    response_description="The Workflow Run",
    responses=build_responses_dict(
        {
            **responses_from_dtos(WorkflowRunReadDTOs, WORKFLOW_RUN_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="get_workflow_run",
)
async def get_workflow_run_api(
    identifier: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowRunReadDTOs, resource_type=WORKFLOW_RUN_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await get_workflow_run(identifier)
    return build_response(response_dto, model, WORKFLOW_RUN_RESOURCE_KIND, version)


# API DELETE @ /api/workflows/run/{identifier}
@router.add_api_route(
    "/run/{identifier}",
    method="DELETE",
    response_model=WorkflowRunReadResponse,
    summary="Delete a Workflow Run",
    response_description="The deleted Workflow Run",
    responses=build_responses_dict(
        {
            **responses_from_dtos(WorkflowRunReadDTOs, WORKFLOW_RUN_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="delete_workflow_run",
)
async def delete_workflow_run_api(
    identifier: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(WorkflowRunReadDTOs, resource_type=WORKFLOW_RUN_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    model = await delete_workflow_run(identifier)
    return build_response(response_dto, model, WORKFLOW_RUN_RESOURCE_KIND, version)


# Event @ workflows/com.event.workflows.run_workflow
@router.add_event_callback(RunWorkflowEvent)
@inject_context
async def run_workflow_callback(event: RunWorkflowEvent, rpc: RPC):
    try:
        response = await run_workflow(
            identifier=event.data.identifier,
            input=event.data.payload,
            wait=False,
            source=event.source,
        )
    except ResourceNotFoundError:
        await logger.aexception("ResourceNotFound", identifier=event.data.identifier)
        response = ("ResourceNotFoundError", event.data.identifier)

    if event.reply_channel and event.correlation_id:
        await rpc.event_bus.publish_response(
            response=response,
            reply_channel=event.reply_channel,
            correlation_id=event.correlation_id,
        )
