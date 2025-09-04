# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Set environment variables placeholders (user should override these)
ENV VSPHERE_HOST=""
ENV VSPHERE_USERNAME=""
ENV VSPHERE_PASSWORD=""

# Run the core_sync module
ENTRYPOINT ["python", "-m", "core_sync"]
