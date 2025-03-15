#!/bin/bash

# Create host_data directory if it doesn't exist
if [ ! -d "host_data" ]; then
    echo "Creating host_data directory for your files..."
    mkdir -p host_data
    echo "# Sample Files" > host_data/README.txt
    echo "Place your PDF, DOCX, TXT and other files in this directory." >> host_data/README.txt
    echo "They will be available to the AI assistant." >> host_data/README.txt
    echo "Created host_data directory with README.txt"
fi

# Check if .env file exists, create if not
if [ ! -f ".env" ]; then
    echo "Creating default .env configuration file..."
    echo "# AI Assistant Configuration" > .env
    echo "HOST_DATA_DIR=./host_data" >> .env
    echo "MODEL_TYPE=dummy" >> .env
    echo "# Uncomment and add your API keys if using language models" >> .env
    echo "# OPENAI_API_KEY=your-api-key" >> .env
    echo "# ANTHROPIC_API_KEY=your-api-key" >> .env
    echo "Created .env file with default configuration"
fi

# Start the containers
echo "Starting AI Assistant..."
docker-compose up --build

# Note: Press CTRL+C to stop the assistant