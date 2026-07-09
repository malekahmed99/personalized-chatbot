# =========================================================
# backend/Dockerfile  (نسخة موحدة تدعم CPU و GPU)
#
# البناء لـ CPU (الافتراضي - ده اللي هتستخدمه انت):
#   docker compose up --build
#
# البناء لـ GPU (لزمايلك):
#   BUILD_MODE=gpu docker compose up --build
# =========================================================

ARG BUILD_MODE=cpu

# الصورة الأساسية بتتغير حسب BUILD_MODE
FROM python:3.13-slim AS base-cpu
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS base-gpu

# دي الحيلة: بنختار أي "base" فعلياً نكمل بيه حسب قيمة BUILD_MODE
FROM base-${BUILD_MODE} AS final
ARG BUILD_MODE
WORKDIR /app

# تثبيت بايثون لو الصورة GPU (Ubuntu عادي مفهوش بايثون بشكل افتراضي)
# ولو CPU الصورة أصلاً فيها بايثون، فالفرع ده هيتجاهل بأمان
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

COPY requirements.txt .

# الفرق الجوهري الوحيد بين النسختين:
# لو gpu: بنجبر pip يعيد تجميع llama-cpp-python بدعم CUDA
# لو cpu: تثبيت عادي زي ما هو مكتوب في requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$BUILD_MODE" = "gpu" ]; then \
        CMAKE_ARGS="-DGGML_CUDA=on" pip install --no-cache-dir \
            llama-cpp-python --force-reinstall --upgrade --no-cache-dir ; \
    fi

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=6 \
  CMD curl -f http://localhost:8000/internal/ready || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
