from fastapi import Response, status

from flowdapt.lib.context import get_context
from flowdapt.lib.rpc import RPCRouter


router = RPCRouter(tags=["health"])


@router.add_api_route(
    "/drain",
    method="POST",
    summary="Activate drain mode",
    response_description="Current drain state",
    status_code=status.HTTP_200_OK,
    name="drain",
)
async def drain_api():
    context = get_context()
    context.flags["draining"] = True
    return Response(
        content='{"draining":true}',
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )


@router.add_api_route(
    "/drain",
    method="DELETE",
    summary="Deactivate drain mode",
    response_description="Current drain state",
    status_code=status.HTTP_200_OK,
    name="undrain",
)
async def undrain_api():
    context = get_context()
    context.flags["draining"] = False
    return Response(
        content='{"draining":false}',
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
