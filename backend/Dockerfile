FROM python:3.12-slim AS base

# Set environment variables to optimize Python behavior inside the container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies if your application needs them (optional)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to take advantage of Docker's layer caching
COPY ./requirements/base.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the rest of your application code
COPY ./app /app

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the FastAPI application using the built-in CLI production server
CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
