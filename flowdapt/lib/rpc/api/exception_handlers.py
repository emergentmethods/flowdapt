from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse

from flowdapt.lib.config import get_configuration


async def ValueErrorHandler(request: Request, exception: ValueError):
    return ORJSONResponse(
        status_code=400, content=jsonable_encoder({"detail": str(exception), "status_code": 400})
    )


async def HTTPErrorHandler(request: Request, exception: Exception):
    app_config = get_configuration()

    if not (detail := getattr(exception, "detail", None)):
        if app_config.dev_mode:
            detail = str(exception)
        else:
            detail = "Internal Server Error"

    status_code = getattr(exception, "status_code", 500)

    return ORJSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"detail": detail, "status_code": status_code}),
    )
