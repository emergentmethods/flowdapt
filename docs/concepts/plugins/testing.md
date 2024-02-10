# Testing Plugins


When developing Plugins, it's important to test them to ensure they work as expected. Flowdapt Plugins are just Python packages, so any testing framework can be used to test them. However, Flowdapt provides tools to make testing Plugins easier. When building Python packages it is a good practice to follow [TDD (Test driven development)](https://en.wikipedia.org/wiki/Test-driven_development) but often times when starting out you want to iterate quickly on the code. We recommend when developing a Plugin that you have the underlying mechanisms needed for the logic separate from the Stage functions. This makes it much easier writing tests for the mechanisms by themselves, then testing the Stages by themselves. This helps ensure you cover all the edge cases and makes it easier to debug when something goes wrong.

Testing Stages can be difficult if you change some code, restart your flowdapt server, potentially update a Workflow YAML and then execute the Workflow. This can be a slow process and can be frustrating when you are trying to iterate quickly. To help with this, Flowdapt provides a utility function called `execute_workflow` that allows you to execute a Workflow from within a test.

## Example

Say you have a Plugin with a `stages.py` that has a Stage that looks like:

```py
def my_awesome_stage():
    print("Hello World!")
```

Assuming our entire Workflow consists of just this stage, you can setup a test for this Stage by creating a `tests/test_stages.py` file that looks like:

```py
import pytest

from flowdapt.compute.executor.local import LocalExecutor
from flowdapt.compute.resources.workflow.execute import execute_workflow
from my_plugin.stages.my_awesome_stage


@pytest.mark.asyncio
async def test_my_workflow():
    result = await execute_workflow(
        {
            "metadata": {
                "name": "my_workflow",
            },
            "spec": {
                "stages": [
                    {
                        "name": "my_awesome_stage",
                        "target": my_awesome_stage,
                    }
                ]
            }
        },
        # If your stage has any inputs, you can pass them here
        input={"some_parameter": "some_value"},
        # This will return the result of the Workflow instead of the Workflow Run
        # and will raise any errors that occur during execution
        return_result=True,
        # You can also specify the namespace used for this execution, but defaults to `default`
        namespace="testing",
        # It defaults to using the LocalExecutor for eager execution, but you can
        # pass any Executor you want here
        executor=LocalExecutor(),
    )
```

As you can see, we call the `execute_workflow` method in the test and pass a dictionary of the Workflow Definition. It takes the exact same shape and size as a Workflow definition from a YAML or JSON. One major difference is instead of passing an import string as the target you can pass the callable directly. Using this tool you can quickly develop and test your Plugins without the hassle of managing the Flowdapt server at the same time.

???+ note "Workflow Definition"
    It is not necessary to define the `kind` parameter in the Workflow definition passed to `execute_workflow`, the dictionary will always be validated as a Workflow Resource.

Some mechanisms of Flowdapt rely on information from the configuration. When testing, you can configure Flowdapt via environment variables. For example, if you are testing a Plugin that does some work with Artifacts, and you want to use in-memory storage for the tests, you can set the protocol to `memory`:

```sh
export FLOWDAPT__STORAGE__PROTOCOL=memory
export FLOWDAPT__STORAGE__BASE_PATH=an_optional_path
```