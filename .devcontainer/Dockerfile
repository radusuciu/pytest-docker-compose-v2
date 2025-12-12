FROM python:3.11.8-bookworm

ARG DEBIAN_FRONTEND=noninteractive
ARG UID=1000
ARG GID=1000
ARG DEV_USER=dev
ARG BUILD_DIR=/tmp/build

ENV VIRTUAL_ENV=/venv
ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

RUN apt-get update \
  && apt-get install -yq --no-install-recommends \
    # useful OS packages
    sudo \
    locales \
    locales-all \
    build-essential \
    openssh-client \
    rsync \
    iputils-ping \
    wget \
    git \
    ripgrep \
    unzip \
    curl \
    vim \
    bash-completion \
    man-db \
    less \
    # Docker CE CLI and other packages
    apt-transport-https \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && update-ca-certificates

RUN addgroup --gid ${GID} ${DEV_USER} \
  && adduser --disabled-password --gecos '' --uid ${UID} --gid ${GID} ${DEV_USER} \
  && mkdir -p /etc/sudoers.d \
  && echo ${DEV_USER} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${DEV_USER} \
  && chmod 0440 /etc/sudoers.d/${DEV_USER} \
  && mkdir -p /home/${DEV_USER} \
  && mkdir -p /home/${DEV_USER}/.vscode-server/extensions \
  && mkdir -p /home/${DEV_USER}/.vscode-server-insiders/extensions \
  && chown -R ${DEV_USER}:${DEV_USER} /home/${DEV_USER}

# install node
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get update \
  && apt-get install -yq --no-install-recommends \
    nodejs \
  && rm -rf /var/lib/apt/lists/* \
  && update-ca-certificates

# install devcontainer cli tool so we can build and push devcontainer from itself
RUN npm install -g @devcontainers/cli
RUN mkdir ${VIRTUAL_ENV} && chown ${UID}:${GID} ${VIRTUAL_ENV}

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

USER ${DEV_USER}

ENV PATH "/home/${DEV_USER}/.local/bin:${PATH}"

# install dependencies into virtualenv
WORKDIR ${BUILD_DIR}
RUN uv venv ${VIRTUAL_ENV}
COPY pyproject.toml uv.lock README.md ${BUILD_DIR}
RUN uv sync --locked

WORKDIR /workspace

LABEL org.opencontainers.image.source https://github.com/radusuciu/pytest-docker-compose-v2
