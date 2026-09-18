# api/ is its own build context - build from here, not the repo root:
#   docker build -t master-splinter-api api/
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copied into an `api/` subdirectory, not flattened into /app, so the
# package's own internal imports (`from api.processors import ...`) resolve
# unchanged - the container recreates the same layout `pythonpath = ["."]`
# gives it in the repo.
COPY . api/

# Cloud Run assigns the port at deploy time via $PORT; 8080 is just the
# default a `docker run -p 8080:8080` without --env PORT will land on.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
