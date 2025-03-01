from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.lib.rpc.eventbus.event import Event
from flowdapt.lib.utils.model import BaseModel


class RunWorkflowEventData(BaseModel):
    identifier: str
    payload: dict = {}


class RunWorkflowEvent(Event):
    channel: str = "workflows"
    type: str = "com.event.workflow.run_workflow"
    data: RunWorkflowEventData


class WorkflowFinishedEvent(Event):
    channel: str = "workflows"
    type: str = "com.event.workflow.workflow_finished"
    data: WorkflowRun


class WorkflowStartedEvent(Event):
    channel: str = "workflows"
    type: str = "com.event.workflow.workflow_started"
    data: WorkflowRun
