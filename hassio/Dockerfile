ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-wheel \
    gcc \
    musl-dev \
    python3-dev

# Create app directory
WORKDIR /app

# Copy Python package files
COPY pyproject.toml /app/
COPY src/todotracker /app/src/todotracker

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages \
    fastapi \
    uvicorn[standard] \
    sqlalchemy \
    pydantic \
    pydantic-settings \
    python-multipart \
    aiosqlite \
    && pip3 install --no-cache-dir --break-system-packages -e /app

# Copy frontend
COPY frontend /app/frontend

# Copy root filesystem
COPY hassio/rootfs /

# Set permissions for S6 scripts
RUN chmod a+x /etc/services.d/todotracker/run \
    && chmod a+x /etc/services.d/todotracker/finish

WORKDIR /
