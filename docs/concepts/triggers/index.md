# Triggers

???+ note "Tools"
    For documentation purposes it is assumed the reader has `flowctl` installed. To see how, please see the repo [README](../../flowctl/index.md#installation). For more information on the trigger commands, see the [trigger](../../flowctl/cli.md#flowctl-trigger) command documentation in `flowctl`.

Flowdapt workflows can be triggered according to custom criteria with the Flowdapt `trigger` service. A trigger resource is defined in its own `yaml` file and follows the same general kubernetes schema as workflows and configs:


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

We see how the above condition is defined as a list of three criteria that all must be satisifed (`eq`) in order to trigger the `action`. The `type` of event must be a `workflow_finished` type, the `data.workflow` of the workflow must be `test_simple`, and the `data.state` of the workflow must be `failed`. 

Once all three of these criteria are met, the trigger service will automatically launch another workflow with the name `fallback_workflow` (which must exist in the database by a previous `flowctl apply -p path/to/workflow.yaml` [details here](../../concepts/workflows/index.md))

## Add the trigger

The example above can be saved into a file called `fallback_trigger.yaml` and then it can be added to the Flowdapt server by running:

```bash
flowctl apply -p /path/to/fallback_trigger.yaml`
```

After it is added, the Flowdapt service will automatically begin monitoring for this event and then triggering the `fallback_workflow` whenever the three criteria are met.

### Setting a `schedule` trigger

The workflow can also be scheduled to periodically re-run itself using the `schedule` key. This type of workflow is good for any workflow that the user knows they want to run on a set frequency such as model retraining, or fetching/updating data at constant intervals in time. Flowdapt adopts the standard `crontab` syntax for setting the schedule which follows:

```yaml
kind: trigger_rule
metadata:
  name: create_features
spec:
  type: schedule
  rule:
    - "*/5 * * * *"
  action:
    target: run_workflow
    parameters:
      workflow: create_features
```

Here the schedule is set to `"*/5 * * * *"` which indicates the `min, hour, dom, mon, dow` where `min` is the minute, `hour` is the hour, `dom` is the day of the month, `mon` is the month, and `dow` is the day of the week (0-6). An asterisk, as used for all entries in the prior example, indicates all times. So the example workflow above will be executed for each minute of each hour of all days of all months. If a user wants to instead run their workflow every 15 minutes, only on Mondays, they could set their `schedule` as `"*/15 * * * 1"`. More details about `crontab` settings can be found [here](https://devhints.io/cron)

As with all other flowdapt resources, the `schedule` trigger can be added to the server with:

```bash
flowctl apply -p /path/to/schedule_trigger.yaml
```

Once it is applied, the schedule becomes activated. The schedule can be removed by deleting the trigger with `flowctl delete -p path/to/schedule_trigger`.

For more information about rules and actions, please see the [rules](../../concepts/triggers/rules.md) and [actions](../../concepts/triggers/actions.md) documentation.