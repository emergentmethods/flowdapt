# syntax=docker/dockerfile:1
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG NON_ROOT_USER=flowdapt

USER root

# Install build dependencies
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get install -y python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install flowml
# TODO: We should probably use a git submodule for this
RUN /opt/venv/bin/pip install --no-cache-dir flowml

USER ${NON_ROOT_USER}

