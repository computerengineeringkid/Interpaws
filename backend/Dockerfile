# Backend Dockerfile
FROM python:3.10-slim

# Prevents Python from writing pyc files and enables stdout/stderr unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /code

# Copy requirements first for better Docker layer caching
COPY requirements.txt /code/

# Install dependencies
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
# Assuming your FastAPI app lives in backend/app
COPY app/ /code/app/

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
