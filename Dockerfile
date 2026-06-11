# Use official lightweight Python image
FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port (documented port)
EXPOSE 8000

# Run Gunicorn WSGI server, dynamically using the PORT environment variable provided by Railway
CMD ["sh", "-c", "gunicorn -w 4 -b 0.0.0.0:${PORT:-8000} main:app"]

