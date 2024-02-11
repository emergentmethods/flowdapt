# Plugins

Flowdapt plugins are a powerful feature that allows for customization and extension of the base functionality in Flowdapt, as well as providing an easy way for users to extend their workflows via custom code.

![flowdapt plugin](../../assets/flowdapt_plugin_light.png#only-light)
![flowdapt plugin](../../assets/flowdapt_plugin_dark.png#only-dark)

A lot of base configurations take what's called a "target" string. This is a string that looks like an import: `my_module.sub_module.my_object`. For example, when configuring the Compute Executor you can specify its target:

```yaml
services:
  compute:
    executor:
      target: flowdapt.compute.executor.ray.RayExecutor
```

This is telling Flowdapt which object definition to use for that component. The rest of the keys passed are the initialization values for that object. This means as a user, you can easily extend certain parts just by specifying your own object definition in that target. This is the same for Stages in a Workflow. The simplest way for a user to make available that class or function is by using Plugins which are simply Python packages with certain configurations that tell flowdapt it's usable as a Plugin.

## Getting Started

Since Flowdapt Plugins are just Python packages, all of the tools that developers use to build and publish packages can be used for Flowdapt plugins. The only difference between a Plugin and any other Python package is a Plugin has what's called an entry point defined for the `flowdapt.plugins` group. This is what tells Flowdapt that this specific package has components that work inside Flowdapt. This also means that if your Plugin has some functionalities that can be reused just like a normal package, then you can install and use it like normal.

## Example

Say you have a Python project setup like:

=== "pyproject.toml"
    ```
    my_package/
    │
    ├── my_package/
    │   ├── __init__.py
    │   ├── module1.py
    │   └── module2.py
    │
    ├── tests/
    │   ├── __init__.py
    │   ├── test_module1.py
    │   └── test_module2.py
    │
    ├── .gitignore
    ├── pyproject.toml
    └── README.md
    ```

=== "setup.py (legacy)"
    ```
    my_package/
    │
    ├── my_package/
    │   ├── __init__.py
    │   ├── module1.py
    │   └── module2.py
    │
    ├── tests/
    │   ├── __init__.py
    │   ├── test_module1.py
    │   └── test_module2.py
    │
    ├── .gitignore
    ├── setup.py
    └── README.md
    ```

The first step to setting it up for Flowdapt is defining the entry point in the packages's metadata. The package's metadata is defined in the project's setup.py file or pyproject.toml. For example:

=== "pyproject.toml"
    ```toml linenums="1" hl_lines="8 9"
    [project]
    name = "my_package"
    version = "0.0.1"
    dependencies = [
        "requests",
    ]

    [project.entry-points."flowdapt.plugins"]
    my_package = "my_package"
    ```

=== "setup.py (legacy)"
    ```py linenums="1" hl_lines="9 10 11 12 13"
    from setuptools import setup

    setup(
        name='my_package',
        version='0.0.1',
        install_requires=[
            'requests',
        ],
        entry_points = {
            'flowdapt.plugins': [
                'my_package = my_package'
            ]
        }
    )
    ```

???+ note "Other tools"
    If you have other tools integrated in your workflow such as Poetry, please consult the documentation on defining entry points.


Once you have the metadata setup, and your package is ready to go, you can simply install the package to the same environment as Flowdapt. For example:

```bash
pip install my_package
```

Now you are ready to use your plugin in Flowdapt! You can reference the package anywhere a target string is accepted such as a Workflow:

```yaml
name: "my_workflow"
description: "My workflow that uses my_package"

stages:
  - target: my_package.module1.my_stage
    name: my_stage
```

???+ note "Template"
    As quality of life to plugin developers, we offer a [cookiecutter](https://github.com/cookiecutter/cookiecutter) template to quickly bootstrap your plugin structure. You can find it [here](https://gitlab.com/emergentmethods/cookiecutter-flowdapt-plugin).