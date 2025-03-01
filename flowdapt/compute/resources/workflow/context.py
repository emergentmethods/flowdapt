from contextvars import ContextVar, Token

from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.lib.utils.model import BaseModel


class WorkflowRunContext(BaseModel):
    input: dict = {}
    namespace: str = "default"
    executor: str

    run: WorkflowRun
    definition: WorkflowResource
    config: dict = {}


_current_context: ContextVar[WorkflowRunContext | None] = ContextVar(
    "_current_context", default=None
)


def get_run_context() -> WorkflowRunContext:
    """
    Get the current WorkflowRunContext.
    """
    if not (context := _current_context.get()):
        raise RuntimeError("No active WorkflowRunContext")
    else:
        return context


def set_run_context(context: WorkflowRunContext):
    """
    Set the current WorkflowRunContext.
    """
    return _current_context.set(context)


def reset_run_context(token: Token):
    """
    Reset the current WorkflowRunContext.
    """
    return _current_context.reset(token)
