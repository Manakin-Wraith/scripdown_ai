FROM python:3.11-slim

# Install system dependencies for WeasyPrint and PyMuPDF
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Railway uses port 8080 by default
EXPOSE 8080

# Run with gunicorn on port 8080
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
