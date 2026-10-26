FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing pyc files and enable stdout buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (gcc, curl, git, libpq-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Global git configuration allowing repo execution across mounted directories
RUN git config --system --add safe.directory "*"

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt

# Create unprivileged application user and set permissions
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -d /home/appuser -s /bin/bash appuser && \
    mkdir -p /app /app/scratch /home/appuser && \
    chown -R appuser:appuser /app /home/appuser

# Copy application source code
COPY --chown=appuser:appuser . .

# Switch to unprivileged non-root user
USER appuser

# Expose port 8000
EXPOSE 8000

# Default entrypoint starts Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
