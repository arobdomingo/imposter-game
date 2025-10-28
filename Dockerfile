# Use Python 3.13 base image
FROM python:3.13

# Copy uv tool (optional, if you're using it)
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

# Set working directory inside container
WORKDIR /app

# Copy only the src folder into /app/src
COPY ./src /app/src
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

# Set PYTHONPATH so imports like user_service.models work
ENV PYTHONPATH=/app/src

# Install dependencies
RUN pip install --no-cache-dir uvicorn fastapi pillow sqlalchemy alembic psycopg2-binary nicegui

# Start FastAPI app
CMD ["uvicorn", "user_service.api:app", "--host", "0.0.0.0", "--port", "8000"]
