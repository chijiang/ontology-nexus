FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy the rest of the application
COPY . .

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Expose the API port
EXPOSE 8000

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
