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

# Install flowml on top of the base environment.
# TODO: We should probably use a git submodule for this
#
# Everything the base image installed is held at its version, so the resolver
# can only add packages. Without that, it is free to make flowml fit by
# replacing flowdapt or one of its dependencies with another version.
#
# flowml 0.1.1 requires pynvml<13, and pynvml 12 requires nvidia-ml-py<13,
# which flowdapt does not allow. flowml never imports pynvml, so the cap is
# lifted here. Drop the override once a flowml release no longer has the cap.
#
# The last step fails the build if flowml does not import, or if flowdapt is
# no longer the copy the base image installed.
RUN /usr/local/bin/pip install --no-cache-dir uv && \
    uv pip freeze --python /opt/venv/bin/python --exclude-editable > /tmp/base-constraints.txt && \
    echo "pynvml>=12" > /tmp/flowml-overrides.txt && \
    uv pip install --no-cache --python /opt/venv/bin/python \
        --constraint /tmp/base-constraints.txt \
        --override /tmp/flowml-overrides.txt \
        flowml && \
    rm /tmp/base-constraints.txt /tmp/flowml-overrides.txt && \
    /opt/venv/bin/python -c "import flowdapt, flowml.models; assert flowdapt.__file__.startswith('/srv/flowdapt/'), flowdapt.__file__"

USER ${NON_ROOT_USER}

