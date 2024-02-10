# Architecture

The architecture of Flowdapt is shown in the figure below:

![flowdapt architecture](../assets/flowdapt-architecture_light.png#only-light)
![flowdapt architecture](../assets/flowdapt-architecture_dark.png#only-dark)

!!! danger "Outdated"
    The architecture diagram is outdated. While it still shows the general structure, we have refactored flowdapt to be executor agnostic, meaning we now provide the ability for users to choose between Ray, Dask, Local, or even their own custom executor. We will update the diagram soon.

The application is designed with a service-oriented architecture (SOA) in mind, where services are independent and can communicate with each other through well-defined interfaces. This architecture allows the application to be easily scalable, maintainable, and testable.

In addition to being built with a service-oriented architecture, Flowdapt is also designed for distributed computing. The application is designed to be deployed in a distributed environment, where services can be scaled horizontally across multiple servers to handle high volumes of requests.

To further enhance the ease of use, Flowdapt is packaged into a single repository, making it easy for developers to set up and deploy the application. This approach simplifies the process of managing and maintaining the application, as all components are centrally managed and can be deployed together as a single unit. The use of a single repository also makes it easy to manage dependencies and ensures that all components of the application are up-to-date and compatible with each other. We also support scaling individual components and services of Flowdapt via configuration to easily go from laptop to cluster.

## Shared Resources

Flowdapt uses a SQL database as a shared resource to store workflow definitions, execution history, and other relevant data. The use of a SQL database ensures data consistency and provides a robust solution for data storage and retrieval. During local single server mode, it is likely that you will use the default SQLite database. This is fine for development and testing, but during production it is advised to move to something more robust such as PostgreSQL.


## Communication

The application uses a message broker for event-based communication between services. This architecture allows services to communicate asynchronously and decouples services from each other. The message broker ensures reliable delivery of messages and provides fault tolerance in case of failures. This defaults to an In-Memory message broker, which is sufficient for a single server setup. We do provide interfaces to other high-availability message brokers for larger clusters.

Flowdapt provides a REST API interface that is used by clients to interact with the server. The REST API is designed to be simple and easy to use, with well-defined endpoints and clear documentation. The use of REST APIs ensures compatibility with a wide range of client applications and provides a standardized interface for accessing the application. We also provide generated SDK's for multiple languages.

---

## Compute Service

The Compute Service is a core component of Flowdapt, and is responsible for managing and executing workflows. Users manage Workflow Definitions via the CLI, the Dashboard, or any other client using the Rest API. Clients can then request Workflows to be executed, though it becomes much more powerful when combined with Triggers, and Experiments to automate some rudimentary tasks and hypotheses.

The Compute Service is designed to be scalable, allowing for the distributed execution of workflows across multiple servers with the help of <a href="https://www.dask.org/" target="_blank">Dask</a> , and is built primarily for ML workloads. Using Dask allows workloads to parallelize the training and prediction of ML models across a variety of frameworks, and adaptively scaling the infrastructure for a greener deployment.


## Trigger Service

The [Trigger Service](../concepts/triggers/index.md) is responsible for providing a flexible and intuitive way for users to schedule workflows to run at specific times or intervals, or based on specific conditions or events.

It is designed to be highly customizable, allowing users to define complex schedules and rules based on various parameters. As such, the Trigger Service plays a crucial role in the scheduling and automation of workflows and events within Flowdapt. Its flexibility and customization options make it a powerful tool for users to streamline their operations and increase productivity.