import re
from typing import Any, Callable, TypeVar

from fastapi import FastAPI, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRoute

from flowdapt.lib.domain.dto.protocol import DTOMapping, RequestDTO, ResponseDTO
from flowdapt.lib.domain.dto.utils import (
    SupportedVersions,
    from_model,
    ref_schema,
    register_schema,
    schema_registry,
)
from flowdapt.lib.domain.models.base import Resource
from flowdapt.lib.errors import APIErrorModel, BadRequestError


CallableT = TypeVar("CallableT", bound=Callable[..., Any])
HeaderAccept = "Accept"
HeaderAPIVersion = "X-API-Version"
APINamespace = "flowdapt.ai"

default_response_models = {
    405: {"model": APIErrorModel},
    403: {"model": APIErrorModel},
}


def build_responses_dict(responses: dict[int, Any] = {}) -> dict[int, Any]:
    """
    Populate the default responses dict with the given responses.

    :param responses: Responses dict
    :return: Responses dict
    """
    return {**default_response_models, **responses}


def compose_content_type(resource_type: str, version: str) -> str:
    """
    Compose the content type for the given resource type and version.

    :param resource_type: Resource type
    :param version: Version
    :return: Content type string
    """
    if resource_type != "json":
        return f"application/vnd.{APINamespace}.{resource_type}.{version}+json"


def extract_version(request_headers: dict, resource_type: str) -> set[str]:
    """
    Extract the API version from the request headers.

    :param request_headers: Request headers
    :param resource_type: Resource type
    :return: Requested versions set
    """
    api_version_header = request_headers.get(HeaderAPIVersion)
    accept_header = request_headers.get(HeaderAccept)

    api_version_header_regex = rf"{resource_type}\.(v\d+(alpha\d+|beta\d+|\.\d+)?)"
    accept_header_regex = rf"application/vnd\.{APINamespace}\.{resource_type}\.(v[0-9a-z]+)\+json;?\s*(?:q=([0-9\.]+))?"  # noqa: E501

    if api_version_header:
        if matched := re.match(api_version_header_regex, api_version_header):
            return {matched.group(1)}
        else:
            raise BadRequestError(detail="Invalid API version header")

    if matches := re.findall(accept_header_regex, accept_header):
        return {
            version[0]
            for version in sorted(matches, key=lambda x: float(x[1]) if x[1] else 1.0, reverse=True)
        }

    return set()


def get_best_version(supported_versions: SupportedVersions, requested_versions: set[str]) -> str:
    """
    Determine the best version from the requested versions.

    :param supported_versions: Supported versions
    :param requested_versions: Requested versions
    :return: Best version
    """
    for version in requested_versions:
        if version in supported_versions:
            return version
    else:
        raise BadRequestError(detail=f"Unsupported API Versions requested {requested_versions}")


async def parse_request_body(request: Request, dto: RequestDTO) -> RequestDTO:
    """
    Parse the request body into the given DTO.

    :param request: Request
    :param dto: Request DTO
    """
    return dto(**await request.json())


def build_response(
    dto: type[ResponseDTO],
    response: Any,
    model_kind: str,
    version: str,
    headers: dict = {},
    recursive: bool = False,
) -> Response:
    """
    Build a response from a response content for the given DTO and model_kind.

    :param dto: Response DTO
    :param response: Response content
    :param model_kind: Model kind
    :param version: The version of the DTO
    :return: Response
    """

    def _process_response_content(response: Any, recursive: bool):
        if isinstance(response, list) and recursive:
            return [from_model(model, dto) for model in response]
        else:
            return from_model(response, dto)

    return ORJSONResponse(
        content=jsonable_encoder(_process_response_content(response, recursive)),
        headers={**headers, HeaderAPIVersion: version},
        media_type=compose_content_type(model_kind, version),
    )


def get_versioned_dto(
    dtos: DTOMapping, resource_type: str
) -> Callable[[Request], tuple[Resource, str]]:
    """
    Get the best versioned DTO for the given resource_type.

    :param dtos: DTOMapping
    :param resource_type: Resource type
    :return: Versioned DTO, version
    """

    async def inner(
        request: Request,
        x_api_version: str | None = Header(None),  # Add this to ensure it is included in spec
    ):
        supported_versions = SupportedVersions(*dtos.keys())
        requested_versions = extract_version(
            request.headers,
            resource_type,
        )

        if not requested_versions:
            requested_versions = {supported_versions.latest()}

        version = get_best_version(supported_versions, requested_versions)
        return dtos[version], version

    return inner


def requests_from_dtos(dtos: DTOMapping, resource_type: str) -> dict:
    """
    Create a requests dict from a DTOMapping for the given resource_type.

    :param dtos: DTOMapping
    :param resource_type: Resource type
    :return: Requests dict
    """
    request_bodies = {"application/json": {"schema": {"oneOf": []}}}

    for version, (request_dto, _) in dtos.items():
        register_schema(request_dto)
        schema = ref_schema(request_dto)

        request_bodies["application/json"]["schema"]["oneOf"].append(schema)
        request_bodies[compose_content_type(resource_type, version)] = {"schema": schema}

    return {"content": request_bodies}


def responses_from_dtos(
    dtos: DTOMapping, resource_type: str, is_array: bool = False, ok_status: int = 200
) -> dict:
    """
    Create a responses dict from a DTOMapping for the given resource_type.

    :param dtos: DTOMapping
    :param resource_type: Resource type
    :param is_array: Whether the response is an array
    :return: Responses dict
    """
    responses = {ok_status: {"content": {}}}

    for version, (_, response_dto) in dtos.items():
        register_schema(response_dto)

        if is_array:
            schema = {"type": "array", "items": ref_schema(response_dto)}
        else:
            schema = ref_schema(response_dto)

        responses[ok_status]["content"].update(
            {compose_content_type(resource_type, version): {"schema": schema}}
        )

    return responses


def openapi_generator(
    app: FastAPI,
    title: str,
    version: str,
    description: str,
) -> Callable:
    """
    Custom OpenAPI generator that allows for custom schemas to be added.

    :param app: FastAPI app
    :param title: API title
    :param version: API version
    :param description: API description
    :return: OpenAPI schema generator method
    """

    def gen_openapi(openapi_version: str = "3.0.2"):
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=title,
            version=version,
            description=description,
            openapi_version=openapi_version,
            routes=app.routes,
        )

        for model_name, schema in schema_registry.items():
            if model_name not in openapi_schema["components"]["schemas"]:
                openapi_schema["components"]["schemas"][model_name] = schema

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return gen_openapi


def generate_custom_openapi_operation_id(route: APIRoute):
    return f"{route.name}"


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name  # in this case, 'read_items'
