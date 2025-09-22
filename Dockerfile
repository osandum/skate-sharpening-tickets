# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

LABEL org.opencontainers.image.source="https://github.com/osandum/skate-sharpening-tickets.git"
LABEL org.opencontainers.image.description="Docker image for skate sharpening tickets application"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.url="https://github.com/osandum/skate-sharpening-tickets"
LABEL org.opencontainers.image.vendor="osandum"
LABEL org.opencontainers.image.version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app_refactored.py
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure all module directories are included
COPY models/ ./models/
COPY services/ ./services/
COPY utils/ ./utils/
COPY routes/ ./routes/
COPY templates/ ./templates/
COPY translations/ ./translations/
COPY migrations/ ./migrations/

# Create instance directory for SQLite database
RUN mkdir -p instance

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app \
    && chmod 755 /app/instance
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=5)"

# Run database migrations and start the application
CMD ["sh", "-c", "flask db upgrade && if [ \"$FLASK_ENV\" = \"production\" ]; then gunicorn --bind 0.0.0.0:5000 --workers 2 app_refactored:app; else python app_refactored.py; fi"]
