# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
# First copy only requirements to leverage Docker cache
COPY ./backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy project
COPY ./backend /app/backend

# Expose port
EXPOSE 8000

# Run app.main:app when the container launches
# Note: For uvicorn to find backend.app.main, the WORKDIR /app needs to be in PYTHONPATH,
# or the command needs to be run from a directory where 'backend' is a discoverable package.
# Uvicorn typically handles this if run from the directory containing the 'backend' package.
# If WORKDIR is /app, and 'backend' is in /app/backend, then 'backend.app.main:app' should work.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
