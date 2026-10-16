ARG PYTHON_IMAGE=python:3.11.15-slim-bookworm
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SPECRAG_BASE_DIR=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN groupadd --system specrag \
    && useradd --system --gid specrag --home /app specrag

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/*.whl && rm -rf /wheels

RUN mkdir -p /app/data /app/process /app/config \
    && chown -R specrag:specrag /app
USER specrag

EXPOSE 8080
CMD ["uvicorn", "specrag.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
