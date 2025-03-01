ARG VARIANT=3.11-bookworm
FROM python:${VARIANT}

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    # Remove imagemagick due to https://security-tracker.debian.org/tracker/CVE-2019-10131
    && apt-get purge -y imagemagick imagemagick-6-common \
    && apt-get install -y jq bat curl git zsh \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and give necessary permissions
# We use the UID 1000 since it is the default UID for the first user on most systems
RUN useradd -u 1000 -G sudo -U -m -s /usr/bin/zsh dev \
    && echo "dev ALL=(ALL) NOPASSWD: /bin/chown" >> /etc/sudoers

# Temporary: Upgrade python packages due to https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-40897 and https://github.com/advisories/GHSA-2mqj-m65w-jghx
# They are installed by the base image (python) which does not have the patch.
RUN python3 -m pip install --upgrade \
    setuptools==69.0.3 \
    gitpython==3.1.41

# Install Taskfile
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
COPY Taskfile.yml /home/dev/Taskfile.yml
# Install dev tools
RUN task -d /home/dev install-devtools

# Setup venv
RUN python3 -m venv /opt/venv
# Chown the venv directory to the non-root user
RUN chown -R dev:dev /opt/venv
# Add the virtual environment to the path amd install poetry
ENV VIRTUAL_ENV="/opt/venv"
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --no-cache-dir uv

# Set the environment variable in the shell's profile to support login shells
# having the virtual environment activated by default
RUN echo 'export PATH=/opt/venv/bin:$PATH' >> /home/dev/.profile

# Switch to the non-root user
USER dev

RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.2.0/zsh-in-docker.sh)"
