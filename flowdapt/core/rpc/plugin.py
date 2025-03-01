from fastapi import Depends, Response, status
from starlette.responses import FileResponse

from flowdapt.core.domain.dto import (
    PluginFilesReadDTOs,
    PluginFilesResponse,
    PluginReadDTOs,
    PluginResponse,
)
from flowdapt.lib.domain.dto.protocol import DTOPair
from flowdapt.lib.errors import APIErrorModel, ResourceNotFoundError
from flowdapt.lib.plugins import (
    PLUGIN_RESOURCE_KIND,
    get_plugin,
    list_plugins,
)
from flowdapt.lib.rpc import RPCRouter
from flowdapt.lib.rpc.api.utils import (
    build_response,
    build_responses_dict,
    get_versioned_dto,
    responses_from_dtos,
)


router = RPCRouter(prefix="/plugin", tags=["plugins"])


@router.add_api_route(
    "/{plugin_name}",
    method="GET",
    response_model=PluginResponse,
    summary="Get information about a specific Plugin",
    response_description="Plugin info",
    status_code=status.HTTP_200_OK,
    responses=build_responses_dict(
        {
            **responses_from_dtos(PluginReadDTOs, PLUGIN_RESOURCE_KIND),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    name="get_plugin",
)
async def get_plugin_api(
    plugin_name: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(PluginReadDTOs, resource_type=PLUGIN_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    return build_response(response_dto, get_plugin(plugin_name), PLUGIN_RESOURCE_KIND, version)


@router.add_api_route(
    "/",
    method="GET",
    response_model=list[PluginResponse],
    summary="List all installed Plugins",
    response_description="List of Plugins",
    status_code=status.HTTP_200_OK,
    responses=build_responses_dict(
        responses_from_dtos(PluginReadDTOs, PLUGIN_RESOURCE_KIND, is_array=True)
    ),
    response_class=Response,
    name="list_plugins",
)
async def list_plugins_api(
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(PluginReadDTOs, resource_type=PLUGIN_RESOURCE_KIND)
    ),
):
    (_, response_dto), version = versioned_dto
    return build_response(
        response_dto, list_plugins(), PLUGIN_RESOURCE_KIND, version, recursive=True
    )


@router.add_api_route(
    "/{plugin_name}/files",
    method="GET",
    response_model=PluginFilesResponse,
    summary="Get a list of files bundled with a Plugin",
    response_description="List of files",
    status_code=status.HTTP_200_OK,
    responses=build_responses_dict(
        {
            **responses_from_dtos(PluginFilesReadDTOs, f"{PLUGIN_RESOURCE_KIND}.files"),
            **{404: {"model": APIErrorModel}},
        }
    ),
    response_class=Response,
    name="list_plugin_files",
)
async def list_plugin_files_api(
    plugin_name: str,
    versioned_dto: tuple[DTOPair, str] = Depends(
        get_versioned_dto(PluginFilesReadDTOs, resource_type=f"{PLUGIN_RESOURCE_KIND}.files")
    ),
):
    (_, response_dto), version = versioned_dto
    files = await get_plugin(plugin_name).list_datafiles()
    return build_response(
        response_dto, [file.name for file in files], f"{PLUGIN_RESOURCE_KIND}.files", version
    )


@router.add_api_route(
    "/{plugin_name}/files/{file_name:path}",
    method="GET",
    summary="Download a file from a specific Plugin",
    response_description="The file requested",
    status_code=status.HTTP_200_OK,
    responses=build_responses_dict(
        {200: {"content": {"application/octet-stream": {}}}, 404: {"model": APIErrorModel}}
    ),
    response_class=Response,
    name="get_plugin_file",
)
async def download_plugin_file_api(plugin_name: str, file_name: str) -> FileResponse:
    plugin = get_plugin(plugin_name)
    data_files = await plugin.list_datafiles()

    for file_path in data_files:
        if file_name == file_path.name:
            return FileResponse(
                file_path, media_type="application/octet-stream", filename=file_path.name
            )

    raise ResourceNotFoundError()
