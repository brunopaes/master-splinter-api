# This directory is its own build context - build from here, whether that's
# `api/` inside the master-splinter monorepo or the root of a standalone
# checkout like master-splinter-api:
#   docker build -t master-splinter-api .   (run from inside this directory)
#   docker build -t master-splinter-api api/   (run from the monorepo root)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# pyproject.toml declares master-splinter/fastapi/uvicorn as regular runtime
# dependencies, so `pip install .` pulls the published master-splinter from
# PyPI - the same as any other external caller - rather than reaching up
# into ../src. Copied and installed before the rest of the source so this
# layer only rebuilds when dependencies change, not on every code edit.
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Cloud Run assigns the port at deploy time via $PORT; 8080 is just the
# default a `docker run -p 8080:8080` without --env PORT will land on.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
