# One image for the API, the workers, migrations, and the seed script (decision 35).
# Which one runs is chosen by the command:
#   API:        uvicorn tracehome.main:app --host 0.0.0.0 --port 8000 --proxy-headers   (default)
#   Worker:     python -m tracehome.worker
#   Migration:  alembic upgrade head   (on AWS: a one-off ECS task)
# No secrets are baked in: every setting comes from environment variables at run time.
#
# Stage order matters: `docker build` without --target builds the LAST stage. The production
# image ("runtime") is therefore last, so a plain build can never ship the test image.

# Base images come from ECR Public, which avoids Docker Hub's pull limits in CodeBuild.
FROM public.ecr.aws/docker/library/python:3.12-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first, so code changes don't reinstall them.
COPY pyproject.toml ./
RUN mkdir -p src/tracehome && touch src/tracehome/__init__.py \
    && pip install . \
    && rm -rf src build

COPY src ./src
RUN pip install --no-deps . && rm -rf build

COPY alembic.ini ./
COPY migrations ./migrations
COPY seed ./seed
COPY scripts ./scripts

# Never run as root inside the container.
RUN useradd --create-home --uid 10001 tracehome


# Test image: the same code plus pytest. Build it with --target test (CodeBuild will too).
FROM app AS test
RUN pip install "pytest>=8,<10" "httpx>=0.27,<1"
COPY tests ./tests
USER tracehome
CMD ["pytest", "-v", "-p", "no:cacheprovider"]


# Production image (the default): no test code, no test tools.
FROM app AS runtime
USER tracehome
EXPOSE 8000
CMD ["uvicorn", "tracehome.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
