# Trigger Actions

Trigger actions are the operations that are executed when a trigger is activated. They define what happens in response to the conditions defined in the trigger rules, such as executing a workflow.

## Run Workflow Action

The `run_workflow` action allows you to execute a specific workflow when the trigger is activated. The action consists of the `run_workflow` target, the name of the workflow to be executed, and optionally the input parameters for the workflow. For example:

```yaml
kind: trigger_rule
metadata:
  name: trigger_scheduled
spec:
  type: schedule
  rule:
    - "* */1 * * *"
  action:
    target: run_workflow
    parameters:
      workflow: my_scheduled_workflow
      input:
        param1: value1
        param2: value2
        param3:
          - value3
          - value4
```
