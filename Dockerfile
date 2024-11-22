# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies, including ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment and install dependencies inside it
RUN python3 -m venv /venv  # Create virtual environment
RUN /venv/bin/pip install --upgrade pip  # Upgrade pip
RUN /venv/bin/pip install -r requirements.txt  # Install dependencies inside venv

# Set the virtual environment path for running the app
ENV PATH="/venv/bin:$PATH"

# Expose the port the app will run on
EXPOSE 3036

# Command to run Gunicorn to serve the Flask app
CMD ["gunicorn", "Tw1zT3ds_IPTV:app", "--workers", "3", "--bind", "0.0.0.0:3037", "--access-logfile", "-", "--error-logfile", "-"]

