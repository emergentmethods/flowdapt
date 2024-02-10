# Workflow Run Context

The `WorkflowRunContext` is an integral part of the Flowdapt workflow execution. It serves as a container that provides access to information related to the current workflow run, such as the input parameters, current namespace, executor details, workflow definition, and current run information. Let's break these components down:

- **Input** (`context.input`): The input parameters passed to the workflow.
- **Namespace** (`context.namespace`): The current namespace that the workflow is running within.
- **Executor** (`context.executor`): The name of the Executor that the workflow is running on.
- **Workflow Definition** (`context.definition`): The structure and details of the workflow Resource.
- **WorkflowRun** (`context.run`): The current run of the Workflow, which includes details such as the start time and the result (once set), as well as the source that triggered the execution.
- **Configuration** (`context.config`): The configuration details from any Config Resources associated with the Workflow.

You can access the `WorkflowRunContext` through the `get_run_context` utility function, which returns the context of the current workflow run. You can use this context to access any of the aforementioned properties.

Here's an example of how to access the `WorkflowRunContext` and use it to retrieve various details of the current workflow execution:

```py
from flowdapt.compute.resources.workflow.context import get_run_context

def stage():
    # Get the current run context
    context = get_run_context()

    # Access properties from the run context
    num_features = context.config["num_features"]  # Retrieve configuration details
    current_workflow_name = context.definition.metadata.name  # Retrieve workflow definition name
    workflow_input = context.input  # Retrieve workflow input
```

Most internal API's that use information from the `WorkflowRunContext` typically automatically get the information, such as the [Object Store](object_storage.md#object-store-api).