# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
# First stage: build environment
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libz-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set up the working directory
WORKDIR /srv/flowdapt

ADD flowdapt ./flowdapt
# Copy the project files and install dependencies
COPY pyproject.toml uv.lock README.md ./

# Create a virtual env
RUN python -m venv /opt/venv

# Install the project and dependencies
RUN UV_PROJECT_ENVIRONMENT="/opt/venv" uv sync --frozen

# Second stage: production environment
FROM python:${PYTHON_VERSION}-slim-bookworm AS production

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libz-dev && \
    apt-get install -y python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user and give necessary permissions
# We use the UID 1000 since it is the default UID for the first user on most systems
RUN useradd -u 1000 -G sudo -U -m -s /bin/bash flowdapt \
    && echo "flowdapt ALL=(ALL) NOPASSWD: /bin/chown" >> /etc/sudoers

# Set up the working directory
WORKDIR /srv/flowdapt

# Copy the virtual environment and code from the builder stage
COPY --from=builder --chown=flowdapt:flowdapt /srv/flowdapt /srv/flowdapt
COPY --from=builder --chown=flowdapt:flowdapt /opt/venv /opt/venv

# Add the virtual environment to the system PATH (same as activating it)
ENV PATH="/opt/venv/bin:$PATH"
# Set the environment variable in the shell's profile to support login shells
# having the virtual environment activated by default
RUN echo 'export PATH=/opt/venv/bin:$PATH' >> /home/flowdapt/.profile

# Default the data directory to /data while running in a container
ENV FLOWDAPT__APP_DIR="/data"
# Deactivate config file persistence and reading by default
# This will just cause the server to use default values
# but can still be overridden by setting this variable
ENV FLOWDAPT__CONFIG_FILE="-"

# Create the data directory and give necessary permissions
RUN mkdir -p /data && chown -R flowdapt:flowdapt /data

# Switch to the non-root user
USER flowdapt
CMD ["flowdapt", "run"]
