# Use Python 3.13 base image
FROM python:3.13

# Copy uv tool (optional, if you're using it)
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

# Set working directory inside container
WORKDIR /app

ENV PYTHONPATH=/app/src

# Install dependencies
RUN pip install --no-cache-dir uvicorn fastapi pillow sqlalchemy alembic psycopg2-binary nicegui

# Start FastAPI app
CMD ["uvicorn", "user_service.api:app", "--host", "0.0.0.0", "--port", "8000"]
