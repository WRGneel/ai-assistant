# Dockerized AI Assistant with File Access

This project provides a containerized AI assistant with advanced file access capabilities. The assistant connects to local files (including PDF and DOCX), making your data accessible through a conversational interface.

## Features

- **Advanced File Access**: Read and process TXT, PDF, DOCX, JSON, and CSV files
- **File Upload Interface**: Upload files directly through the web UI
- **Simple Web Interface**: Chat with your assistant in a clean interface
- **Docker Containerization**: Run everything in containers without local dependencies
- **Extensible Architecture**: Add your own AI models and data connectors

## Quick Start

1. Install Docker and Docker Compose on your system
2. Clone this repository
3. Run the startup script to initialize everything:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
4. Access the interface in your browser at: http://localhost:7860

## Working with Files

The assistant can access and analyze these file types:
- Text files (.txt)
- PDF documents (.pdf)
- Word documents (.docx)
- JSON files (.json)
- CSV files (.csv)

### Adding Files

Two ways to add files:
1. **Direct Upload**: Use the web interface's "Upload Files" tab
2. **Host Directory**: Place files in the `host_data` directory

### File Commands

In the chat interface, you can use:
- `list files` - Show all available files
- `read file: filename.txt` - Display file contents
- `refresh files` - Update after adding files to host directory
- Ask questions about file content - "What's in the sales report PDF?"

## Project Structure

- `app.py`: Main application with Gradio UI
- `file_handler.py`: File access and processing
- `file_upload_handler.py`: UI file upload handling
- `model_loader.py`: AI model integration
- `retrieval_system.py`: Information retrieval
- `database_connector.py`: Database access (optional)
- `start.sh`: Initialization script for easy setup

## Data Access Components

The assistant includes several data access components:

- **File Handlers**: Process text, JSON, CSV, PDF, and DOCX files
- **Retrieval System**: Find relevant information based on user queries
- **Model Loader**: Interface with different AI models
- **Database Connectors**: Connect to databases (optional)

## Customizing the Assistant

### Changing the AI Model

Edit `docker-compose.yml` to set the model type:

```yaml
environment:
  - MODEL_TYPE=transformers  # Options: dummy, transformers, langchain
  - MODEL_NAME=gpt2  # Or other model name
```

### Connecting to Your Data

You can configure where the assistant looks for files:

1. **Default location**: Files in the `./host_data` directory
2. **Custom location**: Set in `.env` file or docker-compose.yml:
   ```
   HOST_DATA_DIR=/path/to/your/data
   ```

## Supporting Libraries

The assistant uses these libraries to handle files:

- **pypdf**: PDF processing and text extraction
- **python-docx**: Word document processing
- **pandas**: Data processing for structured files

## Development Workflow

The local directory is mounted to the container, so you can edit files locally and see changes by refreshing the browser (no container rebuild needed).

For dependency changes:
1. Update `requirements.txt`
2. Rebuild the container: `docker-compose up --build`

## Troubleshooting

- **File access issues**: Check that the host directory is correctly mounted
- **PDF/DOCX not loading**: Verify libraries are installed in the container
- **Error messages**: Check Docker logs with `docker-compose logs`

## Next Steps

- Add a proper vector database for semantic search
- Implement document chunking for large files
- Add user authentication
- Create specialized processing for different document types
- Implement caching for faster responses

## License

This project is provided as open source. Feel free to modify and extend it for your needs.
 different data types (spreadsheets, images, etc.)
- Implement a caching mechanism for faster responses
- Add automated data refresh mechanisms

## Model Integration Options

### Local Models

The assistant supports loading local Hugging Face models:

1. Set `MODEL_TYPE=transformers` in your environment
2. Specify the model name (e.g., `MODEL_NAME=gpt2`)
3. If using larger models, ensure enough resources are allocated to Docker

### API-based Models

To use OpenAI, Anthropic, or other API-based models:

1. Set `MODEL_TYPE=langchain` in your environment
2. Specify your chosen provider's API key
3. Set the model name for the specific provider

## Troubleshooting

- **Container fails to start**: Check Docker logs with `docker-compose logs`
- **Model loading errors**: Ensure you have sufficient memory allocated to Docker
- **File access issues**: Check volume mounts and file permissions
- **Database connectivity**: Verify connection strings and ensure the database is accessible

## License

This project is provided as open source. Feel free to modify and extend it for your needs.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.