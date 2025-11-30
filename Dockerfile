# Dockerfile for I-TUTOR Frontend
# Phase 8 MVP - Streamlit UI
# Build: docker build -t i-tutor-frontend .
# Run: docker run -p 8501:8501 i-tutor-frontend

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLEXSRFPROTECTION=false \
    STREAMLIT_SERVER_ENABLECORS=false \
    STREAMLIT_LOGGER_LEVEL=info

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "frontend/app_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
