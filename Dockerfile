# Use official lightweight Python image
FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies (none required for pure client-side PDF)

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

