# =============================================================================
# backend/Dockerfile — Unified CPU + GPU image
#
# This single Dockerfile handles both CPU-only and GPU-accelerated builds.
# The build target is controlled by the BUILD_MODE build argument:
#
#   CPU build (default — no special hardware required):
#     docker compose up --build
#
#   GPU build (requires an NVIDIA GPU + CUDA driver on the host):
#     BUILD_MODE=gpu docker compose up --build
# =============================================================================

# BUILD_MODE defaults to "cpu" unless explicitly overridden at build time.
ARG BUILD_MODE=cpu

# ---------------------------------------------------------------------------
# Declare two possible base images, one for each mode.
# Only the one selected by BUILD_MODE will actually be used.
# ---------------------------------------------------------------------------
# CPU base: official slim Python image — small footprint, Python pre-installed.
FROM python:3.13-slim AS base-cpu

# GPU base: NVIDIA's CUDA development image on Ubuntu — provides the CUDA
# compiler (nvcc) and libraries needed to build llama-cpp with GPU support.
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS base-gpu

# ---------------------------------------------------------------------------
# Select the active base image based on BUILD_MODE.
# "base-${BUILD_MODE}" resolves to either "base-cpu" or "base-gpu" above.
# ---------------------------------------------------------------------------
FROM base-${BUILD_MODE} AS final
ARG BUILD_MODE
WORKDIR /app

# ---------------------------------------------------------------------------
# System dependency installation.
#
# GPU path: The NVIDIA Ubuntu image ships without Python, so we install it
#           manually alongside the build tools required to compile C extensions.
#
# CPU path: The Python slim image already has Python; we only need the build
#           tools (cmake, git, etc.) for compiling native packages.
# ---------------------------------------------------------------------------
RUN if [ "$BUILD_MODE" = "gpu" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            python3.11 python3-pip python3.11-dev build-essential cmake git curl \
        && rm -rf /var/lib/apt/lists/* \
        && ln -sf /usr/bin/python3.11 /usr/bin/python \
        && ln -sf /usr/bin/pip3 /usr/bin/pip ; \
    else \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential cmake git curl \
        && rm -rf /var/lib/apt/lists/* ; \
    fi

# Copy only the dependency manifest first so Docker can cache this layer.
# If requirements.txt hasn't changed, Docker skips re-installing packages.
COPY requirements.txt .

# ---------------------------------------------------------------------------
# Python dependency installation.
#
# CPU path: Standard pip install from requirements.txt.
#
# GPU path: After the standard install, llama-cpp-python is force-reinstalled
#           from source with the GGML_CUDA flag enabled. This compiles the
#           library against the CUDA toolkit so inference runs on the GPU.
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$BUILD_MODE" = "gpu" ]; then \
        CMAKE_ARGS="-DGGML_CUDA=on" pip install --no-cache-dir \
            llama-cpp-python --force-reinstall --upgrade --no-cache-dir ; \
    fi

# Copy the rest of the application source code into the container.
COPY . .

# Expose the port the FastAPI server will listen on.
EXPOSE 8000

# ---------------------------------------------------------------------------
# Health check: Docker will periodically call this endpoint.
# The backend is considered "healthy" only after the LLM has finished loading,
# which can take up to 90 seconds — hence the generous start-period.
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=6 \
  CMD curl -f http://localhost:8000/internal/ready || exit 1

# Start the FastAPI application using Uvicorn.
# workers=1 is intentional: the LLM is not thread-safe and must not be shared.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
