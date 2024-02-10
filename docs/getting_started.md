# Getting Started

Welcome to the Getting Started guide for Flowdapt. This page will guide you through the installation process, explain the basic configuration, and show you how to create and run your first workflow.

## Installation

You can install Flowdapt natively using a python package manager or via the Docker image.

### Native Installation

You can use pip to install `flowdapt` to your environment, and optionally `flowctl`:

```bash
pip install flowdapt flowctl
```

### Docker

If you prefer to use Docker, you can use the example Docker Compose files provided in our repository. The Docker images available include:

- `flowdapt:latest`: Contains only Flowdapt for a lightweight installation using the latest version.
- `flowdapt:0.1.0`: A specific version tag to use.
- `flowdapt:0.1.0-full`: Includes all the necessary components for a full installation, including FlowML.
- `flowdapt:0.1.0-gpu`: Includes GPU support for running workloads with CUDA.
- `flowdapt:0.1.0-gpu-full`: Includes GPU support and all the necessary components for a full installation.

The images are hosted on the Github Container Registry, and you can pull them using the following command:

```bash
docker pull ghcr.io/emergentmethods/flowdapt:latest
```

You can also run Flowdapt using the example docker compose files provided in the repository. Here are the general steps:

 1. Make sure Docker is installed on your machine, and your user account has access to run the `docker` commands. The general steps can be found here: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)

 2. Open a terminal and navigate to the example directory in the Flowdapt repository:
    ```bash
    cd /path/to/flowdapt/example
    ```

 3. Run the following command to start the containers:
    ```bash
    docker compose -f complete.yaml up -d
    ```

Now Flowdapt and several other services should be running in Docker containers, and you can interact with it as usual. The `complete.yaml` file provides an example single-server deployment, and the other example files provided are used for development and testing purposes.

## Configuration

Flowdapt makes use of a YAML or JSON configuration file. The configuration file allows you to customize settings such as database connections, logging, RPC, services, and storage. You can also change the configuration directory and file name using command line arguments.


### Example Configuration
Here is an example of a Flowdapt configuration:

```yaml
database:
  target: flowdapt.lib.database.storage.tdb.TinyDBStorage

logging:
  level: INFO

rpc:
  api:
    host: 127.0.0.1
    port: 8080
  event_bus:
    url: memory://

services:
  compute:
    executor:
      target: flowdapt.compute.executor.ray.RayExecutor
      cpus: 4
      gpus: 2
      memory: 8GB
```

By default Flowdapt will use a disk-based database for persisting information as well as use the [LocalExecutor](concepts/executor/local.md) for running workloads. 

For further reference on what configuration options are available, see the [Configuration Reference](reference/configuration.md) page, as well as the correspnding reference pages for the defineable components such as the [Database](reference/database/tinydb.md).


### Configuration Directory and File

By default, Flowdapt looks for the configuration file at `~/.flowdapt/flowdapt.yaml`. To specify a different configuration directory or file name, use the following command line arguments:

| Option       | Description              | Example               |
|--------------|--------------------------|-----------------------|
| `--app-dir` | Set the application directory | `flowdapt --app-dir some_dir/ COMMAND` |
| `--config-file` | Set the configuration file name relative to the configs dir | `flowdapt --config-path my_config.yml COMMAND` |


If the app directory and/or the configuration file do not exist, it will be created with the default values.

## Running Your First Workflow

To get started, run the server using the following command:

```bash
flowdapt run
```

[Workflows](concepts/workflows/index.md) are sets of stages that the server should run in sequence. They consist of a definition file that specifies the Python functions to run as Stages, and their information such as name, description, and dependencies. Most Plugins come with pre-defined workflows that you can use out of the box, and for this example we'll use the Openmeteo Plugin.

First, we need to install the Openmeteo Plugin into the same environment you have Flowdapt installed:

```bash
pip install flowdapt-openmeteo-plugin
```

Next, we must install any resources that are defined for the Plugin if applicable. In this case, the Openmeteo Plugin defines some Workflows, Configs, and Triggers so we must add them to Flowdapt:

```bash
flowctl apply -p path/to/openmeteo/resources
```

Now, we can run the Create Features workflow to get things kicked off:

```bash
flowctl run openmeteo_create_features --no-wait
```

This will execute the `openmeteo_create_features` workflow, which will download the latest data from the [OpenMeteo API](https://open-meteo.com/) and create the feature dataframes. Afterwards, a trigger will automatically start the `openmeteo_train` workflow, then finally the `openmeteo_predict` workflow. We used the `--no-wait` flag to return control to the terminal immediately, but you can omit this flag to wait for the workflow result before returning.

You will always get the information about the current run back when running a workflow including the ID and the name, so you can see the status and get the result later on. To see the status of the current run, use the following command:

```bash
flowctl get run <ID-or-name-of-Workflow-Run>
```

Congratulations, you're now up and running with Flowdapt! Continue exploring the documentation to discover more features and capabilities.