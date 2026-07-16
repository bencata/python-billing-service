FROM ghcr.io/astral-sh/uv:python3.12-slim

WORKDIR /app

# Enable bytecode compilation and optimization
ENV UV_COMPILE_BYTECODE=1

# Copy dependencies declaration
COPY pyproject.toml .

# Install dependencies using uv globally (system-wide) in the container
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application source code
COPY . .

# Create directory for SQLite shared volume
RUN mkdir -p /data

EXPOSE 8000
