FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directories
RUN mkdir -p /app/data/files /app/data/documents /app/data/host_files /app/data/database

# Copy application code
COPY . .

# Run a test to check PDF and DOCX libraries
COPY check_libraries.py .
RUN python check_libraries.py

# Expose the port Gradio will run on
EXPOSE 7860

# Command to run the application
CMD ["python", "app.py"]