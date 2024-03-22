# Object Storage

Often times a Workflow or Stage will create an object, such as dataframe, array, model file, or arbitrary python object, that needs to be re-used in a different stage or workflow. In real-time adaptive modeling environments, the frequent movement of these objects requires fast and efficient handling to avoid slowdowns. Flowdapt provides an accelerated interface, called the Object Store, for persisting objects between Workflow and Stage executions. It simplifies data storage and retrieval by automatically managing object persistence and directing objects to Cluster Memory (fast, ephemeral storage) or Artifacts (slower, persistent storage) depending on a variety of factors including the backend (Ray vs Dask) and user control.

## Object Store API

The Object Store is a high-level interface for persisting objects between workflow and stage executions. It simplifies data storage and retrieval by automatically managing object persistence to Cluster Memory and Artifacts both. 

### Usage

You can easily use the Object Store API within your stage functions with three main functions: **put**, **get** and **delete**.

Here's a basic example of how to use the API:

```py
import pandas as pd
from flowdapt.compute.object_store import put, get, delete

def prepare_dataframe():
    # Create the dataframe
    df = pd.Dataframe(np.random.rand(10,100))

    # You can choose the strategy for persisting objects. The available options
    # are "artifact", "cluster_memory" and "fallback".
    # If "artifact" is chosen, the object will be stored/retrieved from distributed storage (Artifacts).
    # If "cluster_memory" is chosen, the object will be stored/retrieved from Cluster Memory.
    # If "fallback" is chosen, the object will be stored/retrieved from Cluster Memory if possible, and
    # from distributed storage (Artifacts) if not.

    # The default strategy is "fallback", however this can be configured via the
    # `services.compute.default_os_strategy` config option.
    put("my_dataframe", df)

    # "artifact" strategy
    put("my_dataframe", df, strategy="artifact")

    # "cluster_memory" strategy
    put("my_dataframe", df, strategy="cluster_memory")

def use_dataframe(prepare_dataframe):
    # Get the object using the default strategy "fallback"
    df = get("my_dataframe")

    # Get the object from distributed storage (Artifacts)
    df = get("my_dataframe", strategy="artifact")

    # Do some calculations

def clear_memory(use_dataframe):
    # Delete the object, if desired, using the default strategy "fallback"
    delete("my_dataframe")

    # Delete the object, if desired, from distributed storage (Artifacts)
    delete("my_dataframe", strategy="artifact")
```

???+ warning "Deprecated"
    The `artifact_only` parameter is deprecated in favor of the `strategy` parameter. The `artifact_only` parameter will be removed in a future release.


### Details

The Object Store is particularly beneficial when dealing with workflows that require data persistence between executions. It prioritizes saving data to Cluster Memory due to its speed and efficiency, but when unable, it defaults to Artifacts. This approach optimizes resource utilization and simplifies data management in workflows.

Please note that the Object Store API is a wrapper around the lower-level Cluster Memory and Artifacts. It is designed to provide a more convenient and intuitive interface for common use-cases, but direct interaction with Cluster Memory and Artifacts may be more suitable for advanced or specific use-cases.

???+ note "Serialization"
    The values that are stored via the Object Store in Cluster Memory or Artifacts must be serializable in some way. This means that the values must be able to be converted to a byte stream and back. This is because the Object Store uses serialization to store and retrieve the values. This is typically not a problem for most python objects, but it is something to be aware of. Flowdapt automatically handles a few different serialization methods, including `pickle` and `json`, but it is possible to manually specify a serialization method if needed.


## Cluster Memory

Cluster Memory acts as a shared memory pool across each of the Worker processes for the Executor. It enables rapid data sharing and communication between different processes within the Executor, facilitating efficient and effective data management for complex workflows.

??? "Ray vs Dask vs Local backend"
    The Object Store API is designed to work with both Ray, Dask, and Local backends without changing any code. Ray allows for Cluster Memory storage of all (serializable) python object types, while Dask only allows Cluster Memory for Dask Dataframes and Dask Arrays. For all other python objects, Dask will default to Artifacts, which means it will be slower since it is bottlenecked by the disk I/O.

### Usage

Cluster Memory can be accessed within your stage functions via the `get_cluster_memory` function. You can then use the Cluster Memory object to store and retrieve data respectively. The `ClusterMemory` object has an API very similar to the Object Store in that there is the **put**, **get**, **delete**, and **clear** methods.

Here's a basic example of how to use Cluster Memory:

```py
from flowdapt.compute.cluster_memory import get_cluster_memory

def create_cities_list():
    # Get the current ClusterMemory
    cluster_memory = get_cluster_memory()
    # Add the cities_list to the memory
    cluster_memory.put("cities_list", ["St. Louis", "Moab", "Los Angeles"])

def use_cities_list():
    # Get the current ClusterMemory
    cluster_memory = get_cluster_memory()
    # Add the cities_list to the memory
    cities_list = cluster_memory.get("cities_list")
```

In the above example, get_cluster_memory is used to obtain a reference to the Cluster Memory. The put method is then used to store a list of cities under the key `"cities_list"`. Then the data is later retrived via the get method in the second stage.

### Details

Cluster Memory is designed to be a simple and efficient solution for sharing data between different Worker processes within an Executor. It is especially beneficial when dealing with workflows that require rapid data sharing or communication between different stages or tasks. However, for workflows that require data persistence beyond the lifetime of an Executor or those that deal with data objects too large to fit in memory, using the Artifacts may be more appropriate.


## Artifacts

Artifacts provide a high-level abstraction for persisting and managing data to a (typically distributed) file system such as local disk or S3, designed for workflows where data needs to be stored and retrieved across different runs or persisted after the lifetime of the Server. The `Artifact` and `ArtifactFile` classes offer a simple and unified interface to various storage backends, made possible by the use of `fsspec` (Filesystem Spec) under the hood.


The main API consists of 2 main classes, and some utility functions.

- `Artifact`: An Artifact is essentially a named container for data files and metadata, stored within a particular namespace. Artifacts support operations like creation, fetching, listing, and deletion, and they also support transactions to allow for operations to be batched and executed at the end of a context.

- `ArtifactFile`: An ArtifactFile represents a file within an Artifact. Each ArtifactFile is linked to its parent Artifact and supports common operations like reading, writing, and deletion.

- `get_artifact`, `list_artifacts`, `new_artifact`: These are the main way to get and use `Artifact` objects. They help infer information from the `WorkflowRunContext` to the Artifacts such as `namespace`, `base_path`, `protocol`, and `params` to make it easier and cleaner when calling the methods.

The `Artifact` object can be used directly but it's highly recommended to use the utility functions to get and create `Artifact` objects.


### Usage

Here's an example of how to use the Artifact system:

```py
from flowdapt.compute.artifacts import new_artifact, get_artifact


def save_artifact_stage():
    # Create a new artifact
    artifact = new_artifact("my_artifact")

    # Add a new file to the artifact and write some content to it
    file = artifact.new_file("my_file", content="Hello, World!")

    # Read from the file
    content = file.read()
    print(content)  # Outputs: "Hello, World!"

def read_artifact_stage():
    # Get an artifact by name
    artifact = get_artifact("my_artifact")

    # Get a reference to a file
    file = artifact.get_file("my_file")
    
    # Read the file
    content = file.read()
    print(content)

    # Now that we have the info, delete the file
    file.remove()

    # We can even delete the entire artifact too
    if artifact.is_empty:
        artifact.delete()
```


### Artifact Metadata

In addition to the data stored within artifacts, each artifact also contains a set of metadata. Metadata in this context is additional information about the artifact that is not part of the artifact's main data content.

Metadata is stored in a special file within the artifact, named .artifact.json. It is a simple key-value store where both keys and values are strings. Metadata is useful for storing extra information about an artifact that can be used to better understand or manage the artifact.

For example, you might want to store the date an artifact was created, the user who created it, the version of the data, or other similar information. This metadata is not directly used by the workflows, but can be extremely useful for tracking and managing your artifacts.

You can interact with an artifact's metadata through the set_meta, get_meta, and del_meta methods of the Artifact class, or by using the Artifact as a dictionary. Here's an example of how to use these methods:

```py
# Create a new artifact
artifact = new_artifact("my_new_artifact")

# Set metadata
artifact.set_meta("created_by", "my_username")
artifact.set_meta("creation_date", "2023-05-26")

# Get metadata
created_by = artifact.get_meta("created_by")
creation_date = artifact.get_meta("creation_date")

# Delete metadata
artifact.del_meta("created_by")

# Use as dictionary
artifact["created_by"] = "my_username"
artifact["creation_date"] = "2023-05-26"

created_by = artifact["created_by"]
```

These methods allow you to set, get, and delete metadata associated with the artifact. This makes it easy to attach additional information to your artifacts and retrieve it later.