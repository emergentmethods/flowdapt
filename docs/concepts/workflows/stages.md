# Stages

Stages are the lowest form of building blocks in Flowdapt. They are Python functions which are chained together to form a Workflow. Stages are defined in the Workflow definition, and are configured to run in a specific order.

## Defining Stages

When defining your Workflow, you can define your Stages in the `stages` key of the Workflow definition. Each stage requires a `name` and `target` key. The `name` is a unique identifier for the stage, and the `target` is the python function to be called. For example:

```yaml
kind: workflow
metadata:
  name: test_workflow
  annotations:
    group: test
spec:
  stages:
    - name: test_stage
      target: user_modules.testing_stuff.test_stage
```

where `user_modules.testing.test_stage` is a python function defined as:

```python
def test_stage() -> list:
    return list(range(10))
```

You can then specify which Stages depend on each other via its `depends_on` key. For example:

```yaml
kind: workflow
metadata:
  name: test_workflow
  annotations:
    group: test
spec:
  stages:
    - name: test_stage
      target: user_modules.testing_stuff.test_stage

    - name: next_stage
      target: user_modules.testing_stuff.next_stage
      depends_on:
        - test_stage
```

where `user_modules.testing.next_stage` is a python function defined as:

```python
def next_stage(rand_array: list) -> None:
    logger.info(f"Got list from test_stage: {rand_array}")
```

By specifying `depends_on` in the `next_stage` definition, we are telling Flowdapt to run `next_stage` after `test_stage` has completed. The `rand_array` argument in `next_stage` will be the value returned by `test_stage`. 

Defining Stages in this way allows users to chain together python functions in a modular way, and Flowdapt will handle the orchestration of the execution. This means it's easy to re-use other pre-defined or custom Stages as building blocks in your Workflows. Additionally, defining two stages with the same `depends_on` will tell Flowdapt that these stages can run in parallel. If then a subsequent stage depends on the previous two parallelized stages, it can define its `depends_on` as:

```yaml
  - name: funnel_stage
    target: user_modules.testing_stuff.funnel_stage
    depends_on:
     - parallel_stage_1
     - parallel_stage_2
```

!!! danger
    If your stages create multiple discrete branches, the best practice is to make a final stage that depends on the last stage of each branch. This ensures that the full workflow is run and that your workflow returns are concatenated into a single return value.


## Stage Arguments

Under the hood, Flowdapt is packing up the `Stage` (python function) and sending it to a worker in the Executor to run. This enables massive parallelization possibilities, but it also means that each `Stage` does not share a scope with any other functions/stages. Instead, data can be passed to the `Stage` via function arguments. 

When a Workflow is executed, you can give it an input. That input is passed as the parameters for the first stage in the Workflow. For example if your first stage takes a parameter called `n_vals`:

```python
def test_stage(n_vals: int) -> list:
    return list(range(n_vals))
```

!!! note "Use the Object Store"
    While passing data directly between stages is easy and helpful, many other cases require more complex object handling. This is why Flowdapt exposes the `Object Store`, which allows you to save an object in one stage/workflow, and fetch it in another via string naming. For more information, see the [Object Store](object_storage.md) documentation.

When running the Workflow, you can pass the input if the first Stage takes any parameters, for example when running a Workflow with `flowctl`:

```bash
flowctl run test_workflow --n_vals 5
```

This will pass the value `5` to the `n_vals` parameter in the `test_stage` function. The return value of the `test_stage` function will then be passed as the parameter to the next Stage in the Workflow, and so on and so forth until the last Stage is finished and the output is returned to the Driver.

!!! hint "`config.input`"
    The input to the workflow can also be obtained via the `get_run_context().config.input` dictionary. This can be obtained in any function that is part of a workflow. This includes stage functions that call other functions. In the present example, it would be equivalent to `n_vals = get_run_context().config.input["n_vals"]`.


## Parameterizing Stages

The previous section shows Stages which are run once per Workflow. However, since Flowdapt is geared for massive parallelization, it includes a special stage type which is `parameterized`. The Workflow defines the Parameterized Stage by adding a `type` key to the Stage definition. For example:

```yaml
kind: workflow
metadata:
  name: build_features
  annotations:
    group: nowcast
spec:
  stages:
    - name: create_city_list
      target: flowdapt_nowcast_plugin.stages.create_city_list

    - target: flowdapt_nowcast_plugin.stages.fetch_city_data
      name: fetch_city_data
      type: parameterized
      depends_on:
          create_city_list
      
    - target: flowdapt_nowcast_plugin.stages.process_city_data
      name: process_city_data
      type: parameterized
      depends_on:
      - fetch_city_data
```

where we see that we set `type` to `parameterized`. The `process_city_data` stage will now run `n` times for each item in the first value returned from the previous stage. In our example, we add the stage `create_cities_list` which would be defined as:

```python
from flowdapt.compute.resources.workflows.context import get_run_context


def create_city_list() -> dict[str, Any]:
    """
    STAGE
    Creates a city list for the subsequent stage to use for parameterization
    """

    # Note: Stages can access the Workflow information from the Run Context
    data_config = get_run_context().config.data_config

    df_cities = get_city_grid(
      data_config["n_cities"],
      data_config["neighbors"],
      data_config["city_data_path"]
    )

    # Convert the DataFrame to a list of dictionaries
    # schema: [{"city": "city_name"}, {"lat": latitude}, {"long": longitude}]
    cities_list = df_cities.to_dict(orient='records')

    return cities_list
```

??? note "Mapping on Values"
    You can pass lists in the Workflow payload with key names that can be used in the `map_on` key. For example, if you pass a list with the key `payload_cities`, you can use `map_on: payload_cities` in the Stage definition to run the Stage once for each item in the list. This payload based map-on functionality is less common since it is not as dynamic as using a stage to define the mapping of a subsequent stage (as shown in the example above).

Now, the parameterized stage called `fetch_city_data` will be run once for each city in `cities_list`. When we define the Parameterized Stage in python, we assume the first argument of the python function will come in as an entry from `cities_list`:

```python
def fetch_city_data(city_dict: dict):
    city = city_dict["city"]
    print(f"Fetching data for {city})
```

So the first argument in the `fetch_city_data` function will be a single entry from `cities_list`. This means the `fetch_data` function should simply use a specific item in the iterable as opposed to the entire iterable. This is because the iterable is split up and sent to different workers to be run in parallel.

???+ note "Mapping on Values"
    The iterable to be mapped on (if no `map_on` key specified) will be the values returned by the previous stage. This can mean that the previous stage returns a list, or it may return a tuple.


## Stage Resources

In Flowdapt, the resource utilization of a Stage can be dictated through the addition of a resources key within the Stage definition. This enables users to define specific resource requirements for each individual Stage. Here's an example of how to implement this:

```yaml
kind: workflow
metadata:
  name: test_workflow
  annotations:
    group: test
spec:
  stages:
    - name: test_stage
      target: user_modules.testing_stuff.test_stage
      resources:
        cpus: 2
        memory: 8GB
        gpus: 1
        custom_resource: 1
```

The fields under resources act as labels within the compute environment, guiding the Executor on where to run the Stages based on available resources. These labels aren't tied to any particular hardware, but rather describe the required resources for the Stage execution.

For instance, if a Stage has a GPU requirement, the Executor will schedule the Stage to run in an environment that has access to a GPU, as long as the Executor itself supports GPU usage and is configured accordingly.

Another common case of resource management is the assignment of a custom named resource. In fact, you can define any custom resource name in your [Executor config](../executor/index.md#configuring-the-executor) at any amount, and then ask for that resource in your stage. For a detailed understanding of how Executors manage these resources, refer to the respective [Executor documentation](../executor/index.md).

???+ note "Resource Labels"
    The [Local Executor](../executor/local.md) does not support resource labels. If you are using the Local Executor, you can still define resource labels in your Workflow, but they will be ignored.


## Accessing the Workflow definition inside Stages

When a Workflow is executed, Flowdapt creates a `WorkflowRunContext` object which holds any information about the current execution including the Workflow definition, and is accessible inside individual Stages (it is also callable from any function called within a stage). Taking the example from earlier, the `fetch_city_data()` function could look something like this:

```python
from flowdapt.compute.resources.workflow.context import get_run_context()

def fetch_city_data():
  context = get_run_context()
  config = context.config
  print(config["study_identifier"])
```

The `get_run_context()` function will return the `WorkflowRunContext` object for the current execution if called from within a Stage. For more information, see the [Workflow Run Context](context.md) documentation.