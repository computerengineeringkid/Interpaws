# Backend Dockerfile
FROM python:3.10-slim

# Prevents Python from writing pyc files and enables stdout/stderr unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /code

# Copy requirements first for better Docker layer caching
COPY requirements.txt /code/

# Install OS and Python dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
# Assuming your FastAPI app lives in backend/app
COPY app/ /code/app/

# Copy Alembic configuration and migrations so `alembic upgrade head` works in the container
COPY alembic.ini /code/
COPY alembic/ /code/alembic/
COPY start.sh /code/start.sh

RUN chmod +x /code/start.sh

# Expose port
EXPOSE 8000

# Default command
CMD ["/code/start.sh"]
