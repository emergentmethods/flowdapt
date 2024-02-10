# Configs

One of the primary advantages of Flowdapt is the ability to easily add configurations to your workflows. For example, you may need to configure parameters such as the number of cities to scrape on (nowcast), or the number of days to forecast. These parameters are easily defined and passed to all functions inside a workflow using the `config` resource.

## Defining a Config

The `config` resource follows a Kubernetes-like schema, just like all Flowdapt resources (e.g. `workflows` and `triggers`):

```yaml
kind: config
metadata:
  name: main
  annotations:
    group: nowcast
spec:
  selector:
    type: annotation
    value:
      group: nowcast
  data:
    study_identifier: "unique-namespace"
    model_train_parameters:
      n_estimators: 100
      max_depth: 5
      random_state: 42
    extras:
      variable1: "value1" # a variable to be used in one of the stages
```

This `config` resource is now available inside any Workflows that have the same `group: nowcast` annotation (as specified by the `selector`). The `config` resource can now be applied with:

```sh
flowctl apply -p path/to/config.yaml
```

???+ example "Config Selector"
    The `selector` field is used to specify which workflows can access the config. In this example, the `selector` is set to `type: annotation` and  the value is a map of annotations `group: nowcast`. This means that any workflows with the annotation `group: nowcast` can access this config. The `selector` can also be set to `type: name` and `value: workflow_name` to allow only the workflow with the name `workflow_name` to access the config.


Now that the `config` resource is applied, it can be used in any workflows that have the same `group: nowcast` annotation. Accessing this config inside any of the stages is as simple as calling `get_run_context().config` from inside any stage or any function called by a stage:

```py
from flowdapt.compute.resources.workflow.context import get_run_context

def my_first_stage():
    # Get the current run context
    context = get_run_context()

    # Access the config
    config = context.config

    # Access the config data using the dictionary syntax
    study_identifier = config["study_identifier"]
    model_train_parameters = config["model_train_parameters"]
    extras = config["extras"]
```

## Modifying a config

One of the biggest benefits of the Flowdapt configuration system is that these configurations (and even workflows) can be modified live via:

- the flowdapt REST API,
- one of the available SDKs,
- flowctl, or
- the flowdapt dashboard

without needing to re-install, no need to re-deploy, and no need to re-build any images. This permits you to rapidly fine tune your plugin for optimal resource management and performance. For example, you can modify the `n_estimators` parameter in the `model_train_parameters` section of the config above, then you can `apply` the config again and the new value will be used in the next run of the workflow.

