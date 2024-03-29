FROM python:3.10-slim as velero-watchdog
LABEL maintainer="DS"

ARG VERSION
ARG BUILD_DATE

ENV BUILD_VERSION=$VERSION
ENV BUILD_DATE=$BUILD_DATE

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    unzip \
    git \
    curl \
    nano && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Set the working directory inside the container
WORKDIR /app

# Copy the project files to the container
COPY ./src /app

# Expose a volume for external access
VOLUME /app/logs

# Set the entry point
CMD ["python3", "-u", "main.py", "--daemon"]
