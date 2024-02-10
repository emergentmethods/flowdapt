from fastapi import Request

from flowdapt.lib.context import ApplicationContext


async def get_context(request: Request) -> ApplicationContext:
    return request.app.state.context
