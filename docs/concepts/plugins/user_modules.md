# User Modules

Sometimes full blown Plugins are too much for what you want to do. In this case, you can use User Modules. User Modules are Python scripts that contain the functions that will be executed by the Workflow. These modules are stored in the application directory, by default it would be `~/.flowdapt/user_modules`. Users can quickly add a Python script to this directory and it will be available to use in their Workflows.

???+ "Location"
    If you use a custom application directory via `--app-dir`, the `user_modules` directory will be in that directory instead.

## Example

Let's say you have a Python script called `user_modules/feature_engineering.py` that contains a function called `process_data()`. You can use this function in your Workflow by defining the `target` as `user_modules.feature_engineering.process_data`. Here's an example:

```yaml
name: "build_features"
description: "Fetch data from online sources, then create features"

stages:
  - target: flowdapt_weather_plugin.stages.fetch_data
    name: fetch_data
    
  - target: user_modules.feature_engineering.process_data
    name: process_data
    depends_on:
     - fetch_data
```

When a Python script is added to the `user_modules` directory, it is automatically added to the path. The import path is always `user_modules` followed by the name of the python module.

Specifying requirements for the User Modules isn't directly supported, however some Executors support specifying packages to install. For example, the RayExecutor supports specifying `pip` field for setting requirements to install in the environment. See the [Ray Executor documentation](../executor/ray.md) for more details. For more complex requirements, it is recommended to create a Plugin.