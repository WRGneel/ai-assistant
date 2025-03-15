# Installation Guide

This guide covers different ways to install and run the AI Assistant with File Access.

## Prerequisites

Before you start, make sure you have:

1. **Python 3.8 or higher** installed (for local installation)
2. **Docker and Docker Compose** installed (for containerized installation)
3. **Git** (optional, for cloning the repository)

## Installation Methods

Choose one of the following installation methods based on your needs:

### Method 1: Docker Installation (Recommended)

This method is recommended for most users as it handles all dependencies automatically.

1. **Clone or download the repository**:
   ```bash
   git clone <repository-url>
   cd ai-assistant
   ```

2. **Create a host data directory** (optional):
   ```bash
   mkdir -p host_data
   ```

3. **Start the container**:
   ```bash
   ./start.sh
   ```

4. **Access the assistant** at http://localhost:7860

### Method 2: Local Installation

This method installs the assistant directly on your system.

1. **Clone or download the repository**:
   ```bash
   git clone <repository-url>
   cd ai-assistant
   ```

2. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the setup script**:
   ```bash
   python setup.py --local
   ```

4. **Start the assistant**:
   ```bash
   python run.py
   ```

5. **Access the assistant** at http://localhost:7860

### Method 3: Development Installation

This method is for developers who want to modify the code.

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ai-assistant
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the setup script**:
   ```bash
   python setup.py --local
   ```

5. **Start the assistant in development mode**:
   ```bash
   python app.py
   ```

6. **Access the assistant** at http://localhost:7860

## Configuration

### Environment Variables

You can configure the assistant using environment variables or a `.env` file:

- `HOST_DATA_DIR`: Path to your files directory (default: `./host_data`)
- `MODEL_TYPE`: Type of AI model to use (`dummy`, `transformers`, `langchain`)
- `MODEL_NAME`: Name of the model (depends on the model type)
- `MODEL_DEVICE`: Device to run the model on (`cpu` or `cuda`)

Example `.env` file:
```
HOST_DATA_DIR=./my_documents
MODEL_TYPE=dummy
MODEL_NAME=gpt2
MODEL_DEVICE=cpu
```

### Using External Models

To use external models via APIs:

1. Add your API keys to the `.env` file:
   ```
   OPENAI_API_KEY=your-api-key-here
   ANTHROPIC_API_KEY=your-api-key-here
   ```

2. Change the model type to `langchain`:
   ```
   MODEL_TYPE=langchain
   MODEL_NAME=gpt-3.5-turbo  # Or another model name
   ```

3. Restart the assistant.

## Troubleshooting

### Common Issues

- **File access errors**: Make sure your files are in the correct directory and have appropriate permissions
- **Model loading errors**: Check that you have enough RAM for the model size
- **Connection errors**: Verify that port 7860 is not being used by another application
- **Missing dependencies**: Run `pip install -r requirements.txt` again

### Docker Issues

- **Container fails to start**: Check Docker logs with `docker-compose logs`
- **Volume mount issues**: Verify your HOST_DATA_DIR path is correct
- **Permission issues**: Ensure the container has read/write access to mounted volumes

### Local Installation Issues

- **Import errors**: Make sure your Python environment has all dependencies
- **Library not found**: Try reinstalling problematic dependencies
- **PDF or DOCX extraction issues**: Verify that pypdf and python-docx are installed correctly

## Updating

To update the assistant:

1. **Docker installation**:
   ```bash
   git pull
   docker-compose down
   docker-compose up --build
   ```

2. **Local installation**:
   ```bash
   git pull
   pip install -r requirements.txt
   python setup.py --local
   ```

## Need Help?

If you encounter issues not covered in this guide, please check the project's issue tracker or forum for assistance.