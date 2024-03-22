# Executors

In the Flowdapt ecosystem, Executors serve as the driving force behind the execution of user-defined Workflows within the compute environment. By acting as a conductor, they navigate the computational workloads, directing these tasks to either a local or external distributed cluster based on the specific Executor employed. This crucial role ensures seamless operation and optimal utilization of available resources, allowing Workflows to be efficiently carried out according to the users' specifications.

There are three types of Executors currently available in Flowdapt:

- **DaskExecutor**: The Dask executor is best suited for larger-than-memory workloads. Dask provides advanced parallelism for analytics, enabling performance at scale.
- **RayExecutor**: The Ray executor is the default choice and is the most versatile for both local and distributed computing. Ray is a flexible, high-performance distributed computing framework.
- **LocalExecutor** (Concurrent.Futures): The LocalExecutor is ideal for testing purposes. It utilizes Python's built-in concurrency features for executing tasks locally.

## Configuring the Executor

You can specify the executor to use in your configuration YAML file under the `services` > `compute` > `executor` section. The executor you wish to use is defined via the target field, which should point to the relevant executor in the Flowdapt application. Here's an example:

```yaml
services:
  compute:
    # the default namespace, this is used for creating buckets
    # in the s3 for saved artifacts
    default_namespace: default
    executor:
      # Use the Ray Executor
      target: flowdapt.compute.executor.ray.RayExecutor
      # Make sure we're seeing logs from the workers
      log_to_driver: True
      # Set any env vars needed
      env_vars:
        OMP_NUM_THREADS: 1
      # We can specify how many resources to assign to the Cluster
      gpus: 1
      cpus: 2
      memory: 8GB
      # Extra logical resources to use when scheduling
      resources:
        hamster_wheels: 6
      # Define the cluster memory actor
      cluster_memory_actor:
        name: actor_name # <---- REQUIRED
        num_cpus: 1
        max_concurrency: 1000
        # if you want to control where the cluster memory actor is placed
        # you can also define the custom resource here (optional)
        resources:
          hamster_wheel: 1
```

By providing a choice of Executors, Flowdapt ensures users can tailor their compute environment to their specific needs. Whether it's the RayExecutor for its flexibility and performance in both local and distributed computing, the DaskExecutor for larger-than-memory workloads, or the LocalExecutor for its convenience in testing, Flowdapt offers solutions to cater to a wide range of computational demands.

For comprehensive details about each Executor and its specific configurations and capabilities, please visit their respective documentation pages.