# syntax=docker/dockerfile:1

# ---- build stage: install dependencies into an isolated venv ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml ./
# Install only the declared runtime dependencies (cached until pyproject changes).
RUN python - <<'EOF' > requirements.txt
import tomllib
print("\n".join(tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"]))
EOF
RUN pip install -r requirements.txt

# ---- runtime stage ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app app ./app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# --no-access-log: uvicorn's access log includes query strings; the app logs requests itself.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
