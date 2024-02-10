# Workflows

Workflows are defined as YAML files that contain the list of stages to be executed, the resources required for each of those stages, and the dependencies for the stages. Similar to all flowdapt resource definitions, the YAML schema follows Kubernetes with `kind`, `metadata`, and `spec` fields:

## Configuring a workflow

```yaml
kind: workflow
metadata:
  name: build_features
  annotations:
    group: nowcast
spec:
  stages:
    - target: flowdapt_nowcast_plugin.stages.fetch_data
      name: fetch_data
      
    - target: flowdapt_nowcast_plugin.stages.process_data
      name: process_data
      depends_on:
      - fetch_data
```

In this example, we set the `kind` as `workflow`, then fill in the `metadata`. Within `metadata`, there is an important field called `annotations` which allows us to define `group` that can all share common traits (for example, we can define a config with the same `group` annotation, and that will ensure that this workflow has full access to the config). The `spec` field contains the `stages` that will be executed. Each stage has a `target` which is the function that will be executed, and a `name` which is the name of the stage. The `depends_on` field is used to define the dependencies of the stage. In this example, the `process_data` stage depends on the `fetch_data` stage, so the `fetch_data` stage will be executed first. 

To apply this resource and make it available to Flowdapt, you can use `flowctl`:

```sh
flowctl apply -p path/to/build_features.yaml
```

where `path/to/workflow.yaml` is the path to the workflow YAML file defined above.

If you want to add a configuration to this workflow (or multiple workflows) then you should define a `config` resource:

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

This `config` resource is now available inside any workflows that have the same `group: nowcast` annotation. Accessing this config inside any of the stages is as simple as calling `get_run_context().config` from inside any stage or any function called by a stage. More information about configuration can be found [here](../configs/index.md).


## Working with Workflows

???+ note "Tools"
    For documentation purposes it is assumed the reader has `flowctl` installed. To see how, please see the repo [README](../../flowctl/index.md#installation).

The easiest route to managing your workflow definitions in Flowdapt will be either via the Dashboard, or using Flowctl. Workflows are what is called a Resource in Flowdapt, and as such, can be managed just like any other resource using the `flowctl get`, `flowctl inspect`, `flowctl apply`, `flowctl delete` commands.

To get a summar of all workflows in the system, you can use the following command:

```sh
flowctl get workflows
```

You can also specify a specific Workflow identifier to narrow it down:
  
```sh
flowctl get workflows build_features
```

This will output a summary of the Resource in a table format. If you want to see the full details of the resource, you can use the `inspect` command:

```sh
flowctl inspect workflow build_features
```

This will output the full details of the resource in YAML format. If you'd like to get raw information about the resource in an alternate format, you can use the `--format` flag with `flowctl get`

```sh
flowctl get workflows --format json
```

The available options are `json`, `yaml`, `table`, and `raw`.

If you want to delete a resource, you can use the `delete` command:

```sh
flowctl delete workflow build_features
```

???+ note "Note"
    The `-p` flag is used to specify the path to the resource files. It must be specified if a resource kind and resource identifier are not specified.

This will delete the resource from the system. If you want to delete multiple resources, the best way is to point the `delete` command at a folder of resource files:

```sh
flowctl delete -p path/to/workflows
``` 

!!! danger "Warning"
    Deleting a resource is irreversible. Please be sure you want to delete the resource before running the `delete` command. If you pass the `-p` option, it will delete all resources in the folder no matter the kind.

Finally since Workflows are executable, you can run them using the `run` command:

```sh
flowctl run build_features
```

If the initial stage of your Workflow requires an input, you can pass it as options to the `run` command:

```sh
flowctl run build_features --n_vals 5
```

This will execute the Workflow and wait until the Workflow is finished, then print the output to the console. If you do not want to wait for the result and just execute it in the background, pass the flag `--no-wait`:

```sh
flowctl run build_features --n_vals 5 --no-wait
```