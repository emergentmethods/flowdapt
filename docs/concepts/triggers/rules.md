# Trigger Rules

Trigger rules are what define the conditions under which a trigger will be activated. 

## Condition Rule

The `condition` rule allows the user to define a set of criteria that must be met when any event occurs in the Flowdapt system. The trigger will then be activated when the criteria are met. The rule consists of a list of conditions in a custom DSL format that looks like this:

```yaml
kind: trigger_rule
metadata:
  name: trigger_fallback_on_fail
spec:
  type: condition
  rule:
    and:
      - eq:
        - var: type
        - com.event.workflow.workflow_finished
      - eq:
        - var: data.workflow
        - test_simple
      - eq:
        - var: data.state
        - failed
  action:
    target: run_workflow
    parameters:
      workflow: fallback_workflow
```

The following operators are supported in the DSL:

- **`eq`** – Checks if two values are equal (`a == b`).
- **`ne`** – Checks if two values are not equal (`a != b`).
- **`gt`** – Checks if the first value is greater than the second (`a > b`).
- **`lt`** – Checks if the first value is less than the second (`a < b`).
- **`ge`** – Checks if the first value is greater than or equal to the second (`a >= b`).
- **`le`** – Checks if the first value is less than or equal to the second (`a <= b`).
- **`and`** – Returns `True` if **all** arguments are truthy (logical AND).
- **`or`** – Returns `True` if **any** argument is truthy (logical OR).
- **`not`** – Returns the logical negation of a single value.
- **`bool`** – Casts the value to a boolean (`True` or `False`).
- **`var`** – Resolves a value from a dot-delimited path in a data dictionary (e.g., `"data.result.x"`).

The `var` operator is a special operator that resolves information from the event data itself. The value of the `var` operator is a dot-delimited path to the value in the event data. For example, if the event data is:

```json
{
  "type": "com.event.workflow.workflow_finished",
  "data": {
    "workflow": "test_simple",
    "state": "failed"
  }
}
```

Then the `var` operator can be used to access the values like this:

```yaml
var: type  # "com.event.workflow.workflow_finished"
var: data.workflow  # "test_simple"
```

The structure of the event data is dependant on the type of event, however all events will have the following fields:

- **`id`** – A unique identifier for the event, generated using `uuid4`.
- **`time`** – The timestamp when the event was created, defaults to the current time.
- **`headers`** – A dictionary of optional metadata or custom headers.
- **`correlation_id`** – An optional ID used to correlate related events.
- **`reply_channel`** – An optional channel to send a reply to.
- **`trace_parent`** – An optional value used for distributed tracing.
- **`channel`** – The channel on which the event was sent.
- **`source`** – The origin of the event.
- **`type`** – A string representing the type or intent of the event.
- **`data`** – The payload or content of the event; type depends on concrete event.

The most common event types are the workflow related events such as the `WorkflowStartedEvent`, and `WorkflowFinishedEvent`. The `data` field of these events follow the same structure as the `WorkflowRun` resource. As an example the full event would look like:

```json
{
  "id": "12345678-1234-5678-1234-567812345678",
  "time": "2023-10-01T12:02:00Z",
  "headers": {},
  "correlation_id": "12345678-1234-5678-1234-567812345678",
  "reply_channel": "reply_channel",
  "trace_parent": "trace_parent",
  "channel": "workflows",
  "source": "compute",
  "type": "com.event.workflow.workflow_finished",
  "data": {
    "uid": "12345678-1234-5678-1234-567812345678",
    "name": "crafty-skunk-61d6c81e",
    "workflow": "my_workflow",
    "source": "api",
    "started_at": "2023-10-01T12:00:00Z",
    "finished_at": "2023-10-01T12:01:00Z",
    "result": [
      "ValueError",
      "You goofed up",
    ],
    "state": "failed"
  }
}
```

## Schedule Rule

The `schedule` rule allows the user to define a cron-like schedule for when the trigger should be activated. The rule consists of a list of cron expressions, for example:

```yaml
kind: trigger_rule
metadata:
  name: run_scheduled
spec:
  type: schedule
  rule:
    - "*/10 * * * *"
  action:
    target: run_workflow
    parameters:
      workflow: scheduled_workflow
      input:
        x: 6
```
