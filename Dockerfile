# Root Dockerfile for the Railway backend service.
#
# Railway builds this monorepo from the repository ROOT (its Railpack builder
# ignores backend/railway.json and cannot auto-detect an app at the root). This
# Dockerfile builds the Flask backend from ./backend so the deploy works without
# depending on a Railway "Root Directory" service setting.
#
# The frontend deploys separately on Vercel and is not affected by this file.

FROM python:3.11-slim

# System libraries required by WeasyPrint (PDF reports) and PyMuPDF.
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

# Install deps first for layer caching.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend application code.
COPY backend/ .

RUN mkdir -p uploads

EXPOSE 8080

# Shell form so ${PORT} (injected by Railway) is expanded; defaults to 8080.
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --timeout 300 --workers 2"]
