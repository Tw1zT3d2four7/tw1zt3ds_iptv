# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies system-wide and create a virtual environment
RUN python3 -m venv /venv  # Create virtual environment
RUN /venv/bin/pip install --upgrade pip  # Upgrade pip
RUN /venv/bin/pip install -r requirements.txt  # Install dependencies inside venv

# Set the virtual environment path for running the app
ENV PATH="/venv/bin:$PATH"

# Expose the port the app will run on
EXPOSE 3036

# Command to run the app
#CMD ["python", "Tw1zT3ds_IPTV.py"]
# Run Gunicorn to serve the Flask app using JSON array syntax for CMD
#CMD ["gunicorn", "Tw1zT3ds_IPTV:app", "--workers", "3", "--bind", "0.0.0.0:3036", "--access-logfile", "-", "--error-logfile", "-"]
CMD ["gunicorn", "Tw1zT3ds_IPTV:app", "--workers", "3", "--bind", "0.0.0.0:3036", "--access-logfile", "-"]

