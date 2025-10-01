FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Base packages
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    python3 \
    python3-pip \
    python3-venv \
    ruby-full \
    build-essential \
    git \
    unzip \
    zip \
    wget \
    libssl-dev \
    libffi-dev \
    openssh-client \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get update && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install global npm packages
RUN npm install -g appium@next npm@latest \
    && appium driver install uiautomator2 \
    && appium driver install xcuitest

# Install mitmproxy
RUN pip3 install --no-cache-dir mitmproxy

# Install fastlane for signing/build automation
RUN gem install fastlane -N

# Python tooling
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Create workspace user
RUN useradd -ms /bin/bash automation && mkdir -p /workspace
WORKDIR /workspace
USER automation

ENV PATH="/home/automation/.local/bin:$PATH"

ENTRYPOINT ["bash"]
