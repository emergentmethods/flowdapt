![logo](docs/assets/logo-white2x.png)

*Flowdapt is a platform designed to help developers deploy adaptive and reactive Artificial Intelligence based applications at large-scale. It is equipped with a set of tools to automatically orchestrate and run dynamic and adaptive machine learning workflows.*

---
![GitLab Release (latest by SemVer)](https://img.shields.io/gitlab/v/release/emergentmethods/flowdapt?style=flat-square)
![GitLab](https://img.shields.io/gitlab/license/emergentmethods/flowdapt?style=flat-square)
<!-- ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/flowdapt?style=flat-square) -->
[![GitHub flowdapt](https://shields.io/badge/GitHub-flowdapt-green?style=flat-square&logo=github)](https://github.com/emergentmethods/flowdapt)
[![Discord](https://dcbadge.limes.pink/api/server/P59QhpknEh)](https://discord.gg/P59QhpknEh)    

Documentation: [https://docs.flowdapt.ai](https://docs.flowdapt.ai)<br>
Source Code: [https://gitlab.com/emergentmethods/flowdapt](https://gitlab.com/emergentmethods/flowdapt)<br>

---

## Why Flowdapt?

We designed Flowdapt to fill the role of cluster orchestration in large-scale real-time adaptive modeling environments. The original devleopment team draws on their experience building software for large-scale AI in supercomputing environments as well as large-scale cloud micro-service architectures. This unique combination resulted in a highly efficient, highly configurable, easily deployable, and easily integrated platform.

The design principles of Flowdapt are focused on:

- 🚲 highly parallelized compute efficiency
- 🤖 automatic resource management and sharing
- 🐞 rapid (local) prototyping and debuggability
- 🔌 intuitive cluster-wide data sharing methods
- ⏱ easy scheduling for real-time applications
- 📝 intuitive configuration and live configurability
- 🚚 deployment cycle efficiency
- 🔬 micro-service-first design
- 🕸 Kubernetes-style schema and behavior

## Example use-cases
- A system designed to adaptively train and inference models for Weather Nowcasting, for thousands of cities simultaneously.
- A scheduled web scraper for finding news, extracting content, summarizing and enriching a strcutured data set, and saving to a vectorDB for other applications to access.
- A single endpoint that takes a user query, then scrapes, summarizes, enriches, and structures hundreds of Reddit threads in parallel, embeds and stores in them in a vector database, and returns the structured summaries back.


## Technical Features
Flowdapt revolves around the concept of Workflows: these are defined and stored in a database, and upon execution, Flowdapt converts them into computational graph of Python functions that are deployed to a cluster. Contrary to other workflow software, Flowdapt is optimized for Artificial Intelligence and Machine Learning challenges. As such, Flowdapt comes with "batteries included":

- **Auto-graph construction** - builds `Ray`, `Dask`, and `Local` graphs automatically
- **Vanilla Python** - Flowdapt does not demand the use of complex concepts and objects (`Ray` and `Dask` objects, decorators, futures, delayeds, graph constructions are all handled automatically by the backend).
- **Scheduling and event driven triggers** - deploy a heterogeneous application that requires real-time adaptivity and event-based reactivity
- **REST API** - deploy to hundreds of thousands of users, control flowdapt from anywhere on the web
- **Scale up** - run on a single machine or a cluster of hundreds of machines without any code changes, robust service based architecture
- **Plug-in** - build your plug-in and install to a large cluster with one command
- **High-performance** - share data cross-process via cluster memory, independent of backend executor
- **Distributed and modular** - run several servers in parallel, scale only the service you need
- **Graphical dashboard** - monitor, build, and launch complex workflows
- **Resource optimized** - Emergent Methods performs in-depth research to build custom methods geared toward reducing electrical costs/GPU time while maintaining equivalent performance and user experience.

These features enable Flowdapt to handle the most challenging machine learning workflows:

- Training, retraining, and fine-tuning thousands of models simultaneously
- Rapid inferencing on those same models
- Distributed data collection/ingestion in real-time

## Overview
For example, a typical user may have three workflows that run at different frequencies or are triggered based on different events:

![Data pipeline](docs/assets/overview.png)

Some of the target use cases for Flowdapt include:

- User-specific, contextual, custom LLM interactions/deployments (e.g. personal assistant for thousands of users simultaneously)
- Real-time adaptive modeling for many-model environments (e.g. forecasting weather for thousands of cities simultaneously)

With extensibility at the core of its design, Flowdapt enables you to extend its functionality through Plugins. Building on top of the already robust ecosystem of Python packages, Plugins themselves are just Python packages that can be installed and imported into Flowdapt. This allows you to easily integrate your own data sources, models, and other custom functionality.

Flowdapt comes with a Rest API and many pre-built SDKs, making it polyglot. We currently have the following SDKS available:

- [Python SDK](https://gitlab.com/emergentmethods/flowdapt-python-sdk)
- [Typescript SDK](https://gitlab.com/emergentmethods/flowdapt-typescript-sdk)

If your application requires another SDK, please reach out to us in the [Flowdapt discord](https://discord.gg/P59QhpknEh) where we can discuss creating a new SDK for your language of choice. 

This documentation aims to assist you in exploring and leveraging all the capabilities of Flowdapt. Whether you're a developer looking to build and optimize machine learning workflows, an administrator setting up and managing the system, or a user creating and modifying workflows and experiments, you'll find the information you need here.


## Credit

Flowdapt is developed and maintained by [Emergent Methods](https://emergentmethods.ai). The team involved includes:

- Timothy Pogue github.com/wizrds
- Elin Törnquist github.com/th0rntwig
- Wagner Costa Santos github.com/wagnercosta
- Robert Caulk github.com/robcaulk

Development and testing of Flowdapt followed a series of important steps:

0. Idea generation and design brainstorming (Oct. 2022)
1. Initial protyping and concept with cluster memory design
2. Testing experimental loads for determining configuration needs and deployment requirements
3. Building Flowdapt on top of Dask as the principal executor, build Flowctl
4. Build FlowML, our ML library tailored for moving models in large-scale systems
5. Preliminary construction of flowdapt-nowcast-plugin and flowdapt-cryptocast-plugin
6. Build flowdapt dashboard
7. Rewriting the entire system to be executor-agnostic and to support Ray with high performance
8. Building the plugin system for Flowdapt to enable easy deployments on local and external clusters
9. Rewrite cluster memory to be user friendly and to have better performance
10. Rewrite flowdapt-nowcast-plugin and deploy new live experiment "Balancing Computational Efficiency with Forecast Accuracy"
11. Build flowdapt-wikipedia-plugin for scraping and summarizing Wikipedia articles at scale
12. Compare Dask vs Ray performance for serviing 250k+ unique models per day in real-time
13. Build and deploy flowdapt-asknews-plugin for talking with the news
14. Rewrite the configuration schema to match Kubernetes schemas and behavior
15. Replace traditional SQL database with document database, upgrade to Pydantic v2.5
16. Build and deploy flowdapt-social-plugin (Reddit scraping and summarization)
17. Open-source (Feb. 2024)

Of course, each step was accompanied by a series of bug fixes, performance improvements, and documentation updates.