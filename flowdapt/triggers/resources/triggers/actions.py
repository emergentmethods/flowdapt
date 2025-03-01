from flowdapt.compute.domain.events.workflow import RunWorkflowEvent, RunWorkflowEventData
from flowdapt.lib.rpc import RPC


async def run_workflow(rpc: RPC, workflow: str, input: dict = {}):
    """
    Trigger action: Run Workflow

    :param workflow: The Workflow to run
    :param input: The input to the Workflow
    """
    await rpc.event_bus.publish(
        RunWorkflowEvent(
            source="trigger", data=RunWorkflowEventData(identifier=workflow, payload=input)
        )
    )


async def print_event(rpc: RPC, workflow: str, input: dict = {}):
    """
    Debugging action: Print Event

    :param workflow: The Workflow to run
    :param input: The input to the Workflow
    """
    print("Trigger Executed!", workflow, input)
