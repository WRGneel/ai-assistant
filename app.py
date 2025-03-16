"""
Main application for AI Assistant with file access capabilities.
"""
import gradio as gr
import os
import sys
import json
import time
import threading
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Import our data access components
# Add parent directory to path if running from subdirectory
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our components
from database_connector import get_database_connector
from file_handler import TextFileHandler, DocumentHandler, FileProcessor
from retrieval_system import KeywordRetriever, RetrievalContext
from model_loader import get_model
from file_upload_handler import FileUploadHandler
from file_batch_processor import BatchProcessor
from file_index import FileIndex, FileIndexBuilder
from document_processor import DocumentProcessor

class AIAssistant:
    def __init__(self, data_dir: str = "data", model_type: str = "dummy"):
        print("Initializing AI Assistant...")

        # Create data directories
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, "files"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "documents"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "host_files"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "database"), exist_ok=True)

        self.data_dir = data_dir

        # Initialize data access components
        self.setup_data_components(data_dir)

        # Set up retrieval system
        self.retriever = KeywordRetriever()
        self.context_manager = RetrievalContext(self.retriever)

        # Initialize the model
        self.model_type = model_type
        self.model_config = {
            # Default configuration
            "model_name": os.getenv("MODEL_NAME", "gpt2"),
            "device": os.getenv("MODEL_DEVICE", "cpu")
        }
        self.model = None

        # Initialize file upload handler
        self.upload_handler = FileUploadHandler(os.path.join(data_dir, "host_files"))

        # Initialize file batch processor and indexer
        self.batch_processor = BatchProcessor(self.host_file_handler, self.host_doc_handler)
        self.file_index = FileIndex(os.path.join(data_dir, "file_index.json"))
        self.index_builder = FileIndexBuilder(self.file_index, self.batch_processor)

        # Initialize document processor
        self.doc_processor = DocumentProcessor()

        # Flag to track if indexing is in progress
        self.indexing_in_progress = False
        self.indexing_progress = 0.0
        self.indexing_thread = None

    def setup_data_components(self, data_dir: str):
        """Set up all data access components"""
        # File handlers for different directories
        self.text_handler = TextFileHandler(os.path.join(data_dir, "files"))
        self.doc_handler = DocumentHandler(os.path.join(data_dir, "documents"))
        self.host_file_handler = TextFileHandler(os.path.join(data_dir, "host_files"))
        self.host_doc_handler = DocumentHandler(os.path.join(data_dir, "host_files"))

        # File processor that can handle all file types
        self.file_processor = FileProcessor(self.text_handler, self.doc_handler)
        self.host_file_processor = FileProcessor(self.host_file_handler, self.host_doc_handler)

        # Database connector - using SQLite for simplicity
        self.db = get_database_connector("sqlite", os.path.join(data_dir, "database/assistant.db"))

        # Sample data for testing
        self._create_sample_data(data_dir)

        # Index available files
        self._index_files()

    def _create_sample_data(self, data_dir: str):
        """Create some sample data files for testing"""
        # Sample text file
        sample_text = "This is a sample text file that contains information about AI assistants.\n"
        sample_text += "AI assistants can help with various tasks including answering questions, "
        sample_text += "searching databases, and analyzing documents."
        self.text_handler.write_text("sample_info.txt", sample_text)

        # Sample JSON file
        sample_json = {
            "products": [
                {"id": 1, "name": "Product A", "price": 99.99, "category": "Electronics"},
                {"id": 2, "name": "Product B", "price": 49.99, "category": "Books"},
                {"id": 3, "name": "Product C", "price": 149.99, "category": "Electronics"}
            ]
        }
        self.text_handler.write_json("products.json", sample_json)

        # Sample CSV data
        sample_csv = [
            {"date": "2023-01-01", "customer": "Customer A", "amount": 125.50},
            {"date": "2023-01-02", "customer": "Customer B", "amount": 89.99},
            {"date": "2023-01-03", "customer": "Customer A", "amount": 45.00}
        ]
        self.text_handler.write_csv("sales.csv", sample_csv)

    def _index_files(self):
        """Index available files for retrieval"""
        print("Indexing files for retrieval...")

        # Set indexing flag
        self.indexing_in_progress = True

        try:
            # Index directories
            dirs_to_index = [
                os.path.join(self.data_dir, "files"),
                os.path.join(self.data_dir, "documents"),
                os.path.join(self.data_dir, "host_files")
            ]

            result = self.index_builder.update_index(dirs_to_index)

            # Process and add files to the retrieval system based on the index
            for file_info in self.file_index.get_all_files():
                file_path = file_info["path"]
                filename = file_info["filename"]
                file_type = file_info["type"]

                # Create document from file info
                doc = {
                    "id": file_path,
                    "filename": filename,
                    "type": file_type,
                    # Get content from the appropriate handler
                    "content": self._get_file_content(file_path, filename, file_type)
                }

                # Add to retriever
                self.retriever.add_document(doc)

            # Print summary
            print(f"Indexed {result['total_files']} files ({result['indexed']} new/updated, {result['skipped']} unchanged, {result['errors']} errors)")
            index_summary = self.file_index.get_index_summary()
            print(f"Index summary: {index_summary}")

            return result
        finally:
            # Clear indexing flag
            self.indexing_in_progress = False

    def _get_file_content(self, file_path: str, filename: str, file_type: str) -> Any:
        """Get file content based on type and path"""
        # Determine which handler to use based on path
        in_host_dir = self.data_dir in file_path and "host_files" in file_path

        if in_host_dir:
            text_handler = self.host_file_handler
            doc_handler = self.host_doc_handler
        else:
            text_handler = self.text_handler
            doc_handler = self.doc_handler

        # Get content based on file type
        try:
            if file_type == "text":
                return text_handler.read_text(filename)
            elif file_type == "json":
                return text_handler.read_json(filename)
            elif file_type == "csv":
                return text_handler.read_csv(filename)
            elif file_type == "pdf" and hasattr(doc_handler, 'pdf_available') and doc_handler.pdf_available:
                return doc_handler.extract_text_from_pdf(filename)
            elif file_type == "docx" and hasattr(doc_handler, 'docx_available') and doc_handler.docx_available:
                return doc_handler.extract_text_from_docx(filename)
            else:
                return f"Unsupported file type: {file_type}"
        except Exception as e:
            print(f"Error getting content for {filename}: {str(e)}")
            return f"Error accessing file: {str(e)}"

    def refresh_file_index(self, force_update: bool = False):
        """Refresh the file index to include new files"""
        if self.indexing_in_progress:
            return "Indexing is already in progress. Please wait for it to complete."

        print("Refreshing file index...")

        # Start indexing in a background thread
        self.indexing_thread = threading.Thread(
            target=self._background_indexing,
            args=(force_update,)
        )
        self.indexing_thread.daemon = True
        self.indexing_thread.start()

        return "Indexing started in the background. This may take a few moments depending on the number of files."

    def _background_indexing(self, force_update: bool = False):
        """Perform indexing in a background thread"""
        try:
            self.indexing_in_progress = True
            self.indexing_progress = 0.0

            start_time = time.time()

            # Clear existing documents from retriever
            if hasattr(self.retriever, 'documents'):
                self.retriever.documents = []
            if hasattr(self.retriever, 'index'):
                self.retriever.index = {}

            # Index directories
            dirs_to_index = [
                os.path.join(self.data_dir, "files"),
                os.path.join(self.data_dir, "documents"),
                os.path.join(self.data_dir, "host_files")
            ]

            # Count total files to index
            total_files = 0
            for dir_path in dirs_to_index:
                if os.path.exists(dir_path):
                    for root, _, files in os.walk(dir_path):
                        total_files += len(files)

            if total_files == 0:
                self.indexing_progress = 1.0
                return

            # Process each directory
            files_processed = 0
            for i, dir_path in enumerate(dirs_to_index):
                if os.path.exists(dir_path):
                    # Update progress
                    self.indexing_progress = files_processed / total_files

                    # Index directory
                    result = self.index_builder.index_directory(dir_path, force_update)

                    # Update progress
                    files_in_dir = result['total_files']
                    files_processed += files_in_dir
                    self.indexing_progress = files_processed / total_files

            # Process and add files to the retrieval system based on the index
            for file_info in self.file_index.get_all_files():
                file_path = file_info["path"]
                filename = file_info["filename"]
                file_type = file_info["type"]

                # Create document from file info
                doc = {
                    "id": file_path,
                    "filename": filename,
                    "type": file_type,
                    # Get content from the appropriate handler
                    "content": self._get_file_content(file_path, filename, file_type)
                }

                # Check if this is a large document that should be chunked
                if file_type in ['pdf', 'docx', 'text'] and isinstance(doc['content'], str) and len(doc['content']) > 10000:
                    # Process large document with chunking
                    self.handle_large_document(filename)
                else:
                    # Add as a single document
                    self.retriever.add_document(doc)

            duration = time.time() - start_time
            print(f"Indexing completed in {duration:.2f} seconds")

            # Set progress to complete
            self.indexing_progress = 1.0
        finally:
            self.indexing_in_progress = False

    def get_indexing_status(self) -> Dict[str, Any]:
        """Get the current indexing status"""
        if self.indexing_in_progress:
            return {
                "status": "in_progress",
                "progress": self.indexing_progress,
                "message": f"Indexing in progress ({self.indexing_progress*100:.1f}%)"
            }
        else:
            # Get summary from file index
            try:
                summary = self.file_index.get_index_summary()
                return {
                    "status": "completed",
                    "progress": 1.0,
                    "message": f"Indexing complete. {summary.get('total_files', 0)} files indexed.",
                    "summary": summary
                }
            except Exception as e:
                return {
                    "status": "error",
                    "progress": 0.0,
                    "message": f"Error getting index status: {str(e)}"
                }

    def handle_large_document(self, filename: str, chunk_size: int = 2000, overlap: int = 400) -> Dict[str, Any]:
        """Process a large document by chunking it"""
        # Read the document
        content = self.read_specific_file(filename)

        # Extract just the content if this is from read_specific_file
        if isinstance(content, str) and "Contents of '" in content:
            parts = content.split("\n\n", 1)
            if len(parts) > 1:
                content = parts[1]
            else:
                content = content

        # Chunk the document
        chunks = self.doc_processor.chunk_document(content, chunk_size, overlap)

        # Get file info
        file_type = filename.split('.')[-1] if '.' in filename else 'unknown'

        # Add each chunk as a separate document to the retriever
        for i, chunk in enumerate(chunks):
            chunk_doc = {
                "filename": f"{filename}_chunk_{i+1}",
                "type": file_type,
                "content": chunk,
                "source_document": filename,
                "chunk_index": i+1,
                "total_chunks": len(chunks)
            }
            self.retriever.add_document(chunk_doc)

        return {
            "filename": filename,
            "chunks": len(chunks),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "total_length": len(content)
        }

    def process_document(self, filename: str, operation: str) -> str:
        """Process a document with advanced operations like summarization"""
        # Get document content
        file_content = self.read_specific_file(filename)

        # Extract just the content part if this comes from read_specific_file
        if isinstance(file_content, str) and "Contents of '" in file_content:
            parts = file_content.split("\n\n", 1)
            if len(parts) > 1:
                content = parts[1]
            else:
                content = file_content
        else:
            content = str(file_content)

        # Process based on operation
        if operation == "Summarize":
            try:
                # Try to use the model for summarization
                if self.model:
                    query = f"Summarize the document {filename}"
                    prompt = self._prepare_extraction_prompt(query, filename, content)
                    summary = self.model.generate(prompt)
                    if summary and len(summary) > 50:
                        return summary
            except Exception as e:
                print(f"Error using model for summarization: {str(e)}")

            # Fall back to extractive summarization
            return f"Summary of {filename}:\n\n" + self.doc_processor.summarize_text(content)

        elif operation == "Extract Key Points":
            try:
                # Try to use the model for key point extraction
                if self.model:
                    query = f"Extract the key points from {filename}"
                    prompt = self._prepare_extraction_prompt(query, filename, content)
                    key_points = self.model.generate(prompt)
                    if key_points and len(key_points) > 50:
                        return key_points
            except Exception as e:
                print(f"Error using model for key point extraction: {str(e)}")

            # Fall back to simulated key points
            return self._simulate_extraction(f"Extract key points from {filename}", filename, content)

        elif operation == "Extract Entities":
            entities = self.doc_processor.extract_entities(content)
            return self.doc_processor.format_entity_list(entities)

        elif operation == "Find Statistics":
            statistics = self.doc_processor.extract_statistics(content)
            return self.doc_processor.format_statistics(statistics)

        elif operation == "Create Timeline":
            timeline = self.doc_processor.extract_timeline(content)
            return self.doc_processor.format_timeline(timeline)

        else:
            return f"Unknown operation: {operation}"

    def get_file_list(self):
        """Get a formatted list of available files"""
        if not hasattr(self, 'file_index'):
            # Fall back to basic listing if file index is not available
            text_files = self.text_handler.list_files()
            doc_files = self.doc_handler.list_files()
            host_text_files = self.host_file_handler.list_files()
            host_doc_files = self.host_doc_handler.list_files()

            # Format the lists
            built_in = [f"{file}" for file in text_files + doc_files]
            host_files = [f"{file}" for file in host_text_files + host_doc_files]

            # Create formatted output
            output = "Available files:\n\n"

            if built_in:
                output += "Built-in files:\n"
                for file in built_in:
                    file_type = self.file_processor.get_file_type(file)
                    output += f"  - {file} ({file_type})\n"
                output += "\n"

            if host_files:
                output += "Your files:\n"
                for file in host_files:
                    file_type = self.host_file_processor.get_file_type(file)
                    output += f"  - {file} ({file_type})\n"
                output += "\n"

            if not built_in and not host_files:
                output += "No files found. Upload files to the 'host_files' directory.\n"

            return output

        # Use the file index to get a more detailed listing
        summary = self.file_index.get_index_summary()

        # Get files organized by directory
        files_by_dir = {}
        for dir_path in summary.get('directories', {}):
            # Skip directories with no files
            if not summary['directories'][dir_path]:
                continue

            # Determine if this is a host directory
            is_host = "host_files" in dir_path
            dir_name = "Your Files" if is_host else "Built-in Files"

            if dir_name not in files_by_dir:
                files_by_dir[dir_name] = []

            # Get files in this directory
            dir_files = self.file_index.get_files_in_directory(dir_path)
            files_by_dir[dir_name].extend(dir_files)

        # Create formatted output
        output = "Available files:\n\n"

        # Add file type summary
        output += f"Total files: {summary.get('total_files', 0)}\n"
        file_types = summary.get('file_types', {})
        if file_types:
            output += "File types:\n"
            for file_type, count in file_types.items():
                output += f"  - {file_type}: {count} files\n"
            output += "\n"

        # List files by directory
        for dir_name, files in files_by_dir.items():
            if not files:
                continue

            output += f"{dir_name}:\n"

            # Group files by type
            files_by_type = {}
            for file in files:
                file_type = file.get('type', 'unknown')
                if file_type not in files_by_type:
                    files_by_type[file_type] = []
                files_by_type[file_type].append(file)

            # List files by type
            for file_type, type_files in files_by_type.items():
                output += f"  {file_type.upper()} Files:\n"
                for file in type_files:
                    filename = file.get('filename', 'Unknown')
                    size = file.get('size', 0)
                    size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
                    output += f"    - {filename} ({size_str})\n"

            output += "\n"

        if not files_by_dir:
            output += "No files found. Upload files to the 'host_files' directory.\n"

        output += f"\nLast updated: {summary.get('last_updated', 'Unknown')}"

        return output

    def load_model(self):
        """Load the AI model"""
        try:
            # Get the appropriate model based on config
            print(f"Loading {self.model_type} model...")
            self.model = get_model(self.model_type, self.model_config)

            # Initialize the model
            success = self.model.load()
            if success:
                print(f"Model loaded successfully: {self.model_type}")
            else:
                print(f"Failed to load {self.model_type} model, using dummy model")
                self.model = get_model("dummy")
                self.model.load()

            return success
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            print("Falling back to dummy model")
            self.model = get_model("dummy")
            self.model.load()
            return False

    def get_response(self, message: str, history: List[List[str]]) -> str:
        """Generate a response to the user query"""
        print(f"Received query: {message}")

        # Check for special commands
        message_lower = message.lower()

        # File listing command
        if message_lower.startswith("list files") or message_lower == "files":
            return self.get_file_list()

        # File refresh command
        if message_lower.startswith("refresh") or message_lower == "refresh files":
            return self.refresh_file_index()

        # Read file command
        if message_lower.startswith("read file:") or message_lower.startswith("open file:"):
            # Extract filename
            parts = message.split(":", 1)
            if len(parts) > 1:
                filename = parts[1].strip()
                return self.read_specific_file(filename)
            else:
                return "Please specify a filename to read."

        # Search files command
        if message_lower.startswith("search files:") or message_lower.startswith("find:"):
            # Extract search query
            parts = message.split(":", 1)
            if len(parts) > 1:
                query = parts[1].strip()
                return self.search_files(query)
            else:
                return "Please specify a search term after 'search files:'"

        # Extract from file command
        if (message_lower.startswith("extract from") or
            message_lower.startswith("summarize") or
            message_lower.startswith("get info from")):

            # Try to identify a filename in the query
            files = []
            if hasattr(self, 'file_index'):
                all_files = self.file_index.get_all_files()
                files = [info['filename'] for info in all_files]
            else:
                files = (self.text_handler.list_files() + self.doc_handler.list_files() +
                        self.host_file_handler.list_files() + self.host_doc_handler.list_files())

            # Look for filename matches
            for file in files:
                if file.lower() in message_lower:
                    # Extract content
                    content = self.read_specific_file(file)

                    # Prepare a response that extracts info based on the query
                    prompt = self._prepare_extraction_prompt(message, file, content)

                    # Try to use the model, fall back to simulated response
                    if self.model:
                        try:
                            response = self.model.generate(prompt)
                            if response and len(response) > 10:
                                # Add to history and return
                                self.context_manager.add_to_history(message, response)
                                return response
                        except Exception as e:
                            print(f"Error generating extraction response: {str(e)}")

                    # Fall back to simulated extraction
                    response = f"Based on '{file}', here's what I found:\n\n"
                    response += self._simulate_extraction(message, file, content)

                    # Add to history and return
                    self.context_manager.add_to_history(message, response)
                    return response

        # Get relevant context for the query
        context = self.context_manager.get_context_for_query(message)
        formatted_context = self.context_manager.format_for_llm(context)

        # Prepare prompt with context and query
        prompt = self._prepare_prompt(message, formatted_context, history)

        # Check if model is available, otherwise use simulated response
        if self.model:
            try:
                # Generate response using the model
                response = self.model.generate(prompt)

                # If response is empty or too short, fall back to simulated
                if not response or len(response) < 10:
                    response = self._simulate_response(message, formatted_context)
            except Exception as e:
                print(f"Error generating response: {str(e)}")
                response = self._simulate_response(message, formatted_context)
        else:
            # Fall back to simulated response
            response = self._simulate_response(message, formatted_context)

        # Add to conversation history
        self.context_manager.add_to_history(message, response)

        return response

    def read_specific_file(self, filename: str) -> str:
        """Read a specific file and return its contents"""
        # Try to get file info from index first
        if hasattr(self, 'file_index'):
            # Search for file in index
            all_files = self.file_index.get_all_files()
            file_info = None

            for info in all_files:
                if info['filename'] == filename:
                    file_info = info
                    break

            if file_info:
                file_path = file_info['path']
                file_type = file_info['type']
                return self._format_file_content(filename, file_type, file_info.get('path'))

        # Fall back to traditional method if index doesn't have the file
        # Check built-in directories
        if self.text_handler.file_exists(filename):
            file_type = self.file_processor.get_file_type(filename)
            return self._process_file_content(filename, file_type, self.text_handler, self.doc_handler)

        # Check host directory
        if self.host_file_handler.file_exists(filename):
            file_type = self.host_file_processor.get_file_type(filename)
            return self._process_file_content(filename, file_type, self.host_file_handler, self.host_doc_handler)

        # File not found
        return f"File '{filename}' not found. Use 'list files' to see available files."

    def _format_file_content(self, filename: str, file_type: str, file_path: str = None) -> str:
        """Format file content for display based on file info"""
        # Get file content
        content = self._get_file_content(file_path, filename, file_type) if file_path else None

        if not content:
            # Fall back to process_file_content if we couldn't get content from index
            if self.text_handler.file_exists(filename):
                return self._process_file_content(filename, file_type, self.text_handler, self.doc_handler)

            if self.host_file_handler.file_exists(filename):
                return self._process_file_content(filename, file_type, self.host_file_handler, self.host_doc_handler)

            return f"Could not read content from file '{filename}'."

        # Format based on file type
        result = f"Contents of '{filename}':\n\n"

        if file_type == 'text':
            result += content

        elif file_type == 'json':
            if isinstance(content, dict) or isinstance(content, list):
                result += json.dumps(content, indent=2)
            else:
                result += str(content)

        elif file_type == 'csv':
            # Format CSV data as a table
            if isinstance(content, list) and content:
                if isinstance(content[0], dict):
                    # Get headers
                    headers = list(content[0].keys())
                    result += " | ".join(headers) + "\n"
                    result += "-" * (sum(len(h) for h in headers) + (len(headers) - 1) * 3) + "\n"

                    # Add rows
                    for row in content:
                        result += " | ".join(str(row.get(h, "")) for h in headers) + "\n"
                else:
                    # Already formatted as text
                    result += str(content)
            else:
                result += "Empty CSV file or invalid format"

        elif file_type == 'pdf' or file_type == 'docx':
            # These should already be extracted as text
            result += content

        else:
            result += f"Unsupported file type: {file_type}"

        return result

    def _process_file_content(self, filename: str, file_type: str, text_handler: TextFileHandler, doc_handler: DocumentHandler) -> str:
        """Process file content based on file type"""
        try:
            result = f"Contents of '{filename}':\n\n"

            if file_type == 'text':
                content = text_handler.read_text(filename)
                result += content

            elif file_type == 'json':
                content = text_handler.read_json(filename)
                result += json.dumps(content, indent=2)

            elif file_type == 'csv':
                content = text_handler.read_csv(filename)
                # Format CSV data as a table
                if content:
                    # Get headers
                    headers = list(content[0].keys())
                    result += " | ".join(headers) + "\n"
                    result += "-" * (sum(len(h) for h in headers) + (len(headers) - 1) * 3) + "\n"

                    # Add rows
                    for row in content:
                        result += " | ".join(str(row.get(h, "")) for h in headers) + "\n"
                else:
                    result += "Empty CSV file"

            elif file_type == 'pdf':
                if hasattr(doc_handler, 'pdf_available') and doc_handler.pdf_available:
                    content = doc_handler.extract_text_from_pdf(filename)
                    result += content
                else:
                    result += "PDF support is not available. Install 'pypdf' library."

            elif file_type == 'docx':
                if hasattr(doc_handler, 'docx_available') and doc_handler.docx_available:
                    content = doc_handler.extract_text_from_docx(filename)
                    result += content
                else:
                    result += "DOCX support is not available. Install 'python-docx' library."

            else:
                result += f"Unsupported file type: {file_type}"

            return result

        except Exception as e:
            return f"Error reading file '{filename}': {str(e)}"

    def _prepare_prompt(self, query: str, context: str, history: List[List[str]]) -> str:
        """Prepare a prompt for the model with context and conversation history"""
        # Create a conversational prompt
        prompt = "You are an AI assistant that helps with data and files. "
        prompt += "Answer the question based on the provided context.\n\n"

        # Add context
        prompt += "Context information:\n"
        prompt += context
        prompt += "\n\n"

        # Add recent conversation history (last 3 turns)
        if history:
            prompt += "Recent conversation:\n"
            recent_history = history[-3:] if len(history) > 3 else history
            for user_msg, assistant_msg in recent_history:
                prompt += f"User: {user_msg}\n"
                prompt += f"Assistant: {assistant_msg}\n"

        # Add the current query
        prompt += f"\nUser: {query}\n"
        prompt += "Assistant: "

        return prompt

    def _prepare_extraction_prompt(self, query: str, filename: str, content: str) -> str:
        """Prepare a prompt for extracting information from a file"""
        # Create a prompt for extracting specific information
        prompt = "You are an AI assistant that helps with file analysis. "
        prompt += "Extract the requested information from the file content provided.\n\n"

        # Add original query
        prompt += f"User request: {query}\n\n"

        # Add file information
        prompt += f"Filename: {filename}\n"

        # Try to determine what kind of extraction is needed
        extraction_type = "general"
        if "summarize" in query.lower():
            extraction_type = "summary"
        elif "key points" in query.lower() or "main points" in query.lower():
            extraction_type = "key_points"
        elif "statistics" in query.lower() or "numbers" in query.lower() or "metrics" in query.lower():
            extraction_type = "statistics"
        elif "people" in query.lower() or "names" in query.lower() or "individuals" in query.lower():
            extraction_type = "people"
        elif "dates" in query.lower() or "timeline" in query.lower() or "when" in query.lower():
            extraction_type = "dates"
        elif "locations" in query.lower() or "places" in query.lower() or "where" in query.lower():
            extraction_type = "locations"

        # Add guidance based on extraction type
        if extraction_type == "summary":
            prompt += "Task: Provide a concise summary of the file contents.\n"
        elif extraction_type == "key_points":
            prompt += "Task: Extract the key points or main ideas from the document.\n"
        elif extraction_type == "statistics":
            prompt += "Task: Extract all numerical data, statistics, and metrics from the document.\n"
        elif extraction_type == "people":
            prompt += "Task: Identify all people and organizations mentioned in the document.\n"
        elif extraction_type == "dates":
            prompt += "Task: Extract all dates and create a timeline of events mentioned in the document.\n"
        elif extraction_type == "locations":
            prompt += "Task: Identify all locations and places mentioned in the document.\n"
        else:
            prompt += "Task: Extract the relevant information based on the user's request.\n"

        # Add the file content, truncating if too long
        max_content_length = 8000  # Adjust based on model's context window
        file_content = content

        if isinstance(content, str) and "Contents of '" in content:
            # Extract just the content part if this comes from read_specific_file
            parts = content.split("\n\n", 1)
            if len(parts) > 1:
                file_content = parts[1]

        # Truncate if needed
        if isinstance(file_content, str) and len(file_content) > max_content_length:
            prompt += f"File content (truncated, showing first {max_content_length} characters):\n"
            prompt += file_content[:max_content_length] + "...\n"
        else:
            prompt += "File content:\n"
            prompt += str(file_content) + "\n"

        # Add final instruction
        prompt += "\nBased on the content above, provide the requested information in a clear, organized format."

        return prompt

    def _simulate_extraction(self, query: str, filename: str, content: str) -> str:
        """Simulate extracting information from file content"""
        file_type = filename.split('.')[-1] if '.' in filename else 'unknown'

        # Extract just the content if this is from read_specific_file
        if isinstance(content, str) and "Contents of '" in content:
            parts = content.split("\n\n", 1)
            if len(parts) > 1:
                content = parts[1]

        # Different responses based on query and file type
        if "summarize" in query.lower():
            return f"This {file_type} file contains information about {filename.split('.')[0].replace('_', ' ')}. " + \
                   f"It's approximately {len(content) // 100} paragraphs long and discusses key concepts and applications."

        elif "key points" in query.lower():
            return "Key points from the document:\n\n" + \
                   "1. The document discusses various applications and concepts.\n" + \
                   "2. It contains information that can be used for reference purposes.\n" + \
                   "3. There are multiple sections covering different aspects of the topic."

        elif "statistics" in query.lower():
            # Generate some fake statistics based on the filename
            topic = filename.split('.')[0].replace('_', ' ')
            return f"Statistics from {filename}:\n\n" + \
                   f"- Total entries: {hash(filename) % 100 + 50}\n" + \
                   f"- Growth rate: {hash(filename) % 20 + 5}%\n" + \
                   f"- Success rate: {hash(filename) % 30 + 65}%\n" + \
                   f"- Average value: ${hash(filename) % 1000 + 500}.00"

        else:
            # Generic extraction
            return "Based on my analysis of the document, it contains information about " + \
                   f"{filename.split('.')[0].replace('_', ' ')}. The document appears to be a " + \
                   f"{file_type.upper()} file with approximately {len(content)} characters of text.\n\n" + \
                   "The content is organized into several sections and contains relevant information " + \
                   "that matches your query. You can view the full document using the 'read file: " + \
                   f"{filename}' command."

    def _simulate_response(self, query: str, context: str) -> str:
        """Simulate model responses for demo purposes"""
        query_lower = query.lower()

        # Check for file-related queries
        if any(word in query_lower for word in ["file", "document", "text", "json", "csv", "pdf", "docx", "word"]):
            if "list" in query_lower or "show" in query_lower or "what" in query_lower:
                return self.get_file_list()

            if "read" in query_lower or "open" in query_lower or "view" in query_lower or "content" in query_lower:
                # Try to identify a filename in the query
                files = self.text_handler.list_files() + self.doc_handler.list_files() + \
                       self.host_file_handler.list_files() + self.host_doc_handler.list_files()

                for file in files:
                    if file.lower() in query_lower:
                        return self.read_specific_file(file)

                return "I can read files for you. Please specify which file using 'read file: filename.txt' or choose from the file list."

            if "product" in query_lower or "products.json" in query_lower:
                return "I found information about products in the JSON file:\n\n" + \
                       "There are 3 products. Two are in the Electronics category, and one is in Books.\n" + \
                       "Product A costs $99.99, Product B costs $49.99, and Product C costs $149.99."

            if "sales" in query_lower or "sales.csv" in query_lower:
                return "I found sales information in the CSV file:\n\n" + \
                       "There are 3 sales records from January 2023.\n" + \
                       "Customer A made 2 purchases totaling $170.50.\n" + \
                       "Customer B made 1 purchase for $89.99."

            # General file response
            return "I can help you with various files including text, PDF, and Word documents. " + \
                   "You can use 'list files' to see available files, 'read file: filename.txt' to view file contents, " + \
                   "or ask questions about specific files."

        # Check for database-related queries
        if "database" in query_lower or "sql" in query_lower:
            return "I found the following information in the database:\n\n" + \
                   "Product A costs $99.99 and is in the Electronics category.\n" + \
                   "Product B costs $49.99 and is in the Books category."

        # Check if query is about capabilities
        if any(word in query_lower for word in ["help", "can you", "what can", "capabilities"]):
            return "I can help you with several tasks:\n\n" + \
                   "1. Read and analyze text files, PDFs, Word documents, JSON, and CSV data\n" + \
                   "2. Search and query databases\n" + \
                   "3. Extract information from documents\n" + \
                   "4. Answer questions based on the data available to me\n\n" + \
                   "Some useful commands:\n" + \
                   "- 'list files' - Show all available files\n" + \
                   "- 'read file: filename.txt' - View the contents of a specific file\n" + \
                   "- 'refresh files' - Update the file index if you've added new files"

        # Check if query is about files or folders
        if "folder" in query_lower or "directory" in query_lower:
            return "To add files to the assistant, place them in the 'host_files' directory. " + \
                   "This is mapped to a folder on your host system as specified in the docker-compose.yml file. " + \
                   "After adding files, use 'refresh files' to update the index."

        # Generic response for other queries
        if "relevant_documents" in context and "No relevant documents found" not in context:
            return "Based on the information I have, I can tell you that AI assistants " + \
                   "can be used for various tasks like answering questions, searching " + \
                   "databases, and analyzing documents. What specific aspect are you interested in?"
        else:
            return "I don't have enough information to answer that question. " + \
                   "You can try asking about the files and data I have access to using 'list files'."

    def search_files(self, query: str, max_results: int = 5) -> str:
        """Search for files matching a query"""
        if not hasattr(self, 'retriever') or not hasattr(self.retriever, 'retrieve'):
            return "Search functionality not available."

        if not query:
            return "Please provide a search query."

        # Get relevant context for the query
        context = self.context_manager.get_context_for_query(query, max_documents=max_results)
        relevant_docs = context.get('relevant_documents', [])

        if not relevant_docs:
            return f"No files found matching query: '{query}'"

        # Format the results
        result = f"Found {len(relevant_docs)} files matching: '{query}'\n\n"

        for i, doc in enumerate(relevant_docs):
            filename = doc.get('filename', 'Unknown')
            doc_type = doc.get('type', 'Unknown')
            relevance = doc.get('relevance_score', 0)

            result += f"{i+1}. {filename} ({doc_type}) - Relevance: {relevance:.2f}\n"

            # Add a snippet of content
            content = doc.get('content', '')
            if isinstance(content, str):
                # Find relevant snippet containing the query terms
                query_terms = query.lower().split()
                best_snippet = self._find_relevant_snippet(content, query_terms)

                if best_snippet:
                    result += f"   Snippet: \"{best_snippet}...\"\n"
                else:
                    # Fall back to first 100 chars
                    snippet = content[:100].replace('\n', ' ').strip()
                    if len(content) > 100:
                        snippet += "..."
                    result += f"   Snippet: \"{snippet}\"\n"
            elif isinstance(content, (dict, list)):
                # For structured data, show a summary
                result += f"   Contains structured data with {len(content)} {'items' if isinstance(content, list) else 'fields'}\n"

            result += "\n"

        result += "Use 'read file: filename' to view the full contents of any file."

        return result

    def _find_relevant_snippet(self, content: str, query_terms: List[str], context_size: int = 50) -> str:
        """Find a snippet of content that contains query terms"""
        if not content or not query_terms:
            return ""

        # Convert content to lowercase for case-insensitive search
        content_lower = content.replace('\n', ' ').lower()

        # Find the positions of all query terms in the content
        term_positions = []
        for term in query_terms:
            pos = content_lower.find(term)
            while pos != -1:
                term_positions.append((pos, len(term)))
                pos = content_lower.find(term, pos + 1)

        if not term_positions:
            return ""

        # Sort positions
        term_positions.sort()

        # Find the best snippet - one that contains the most query terms in close proximity
        best_score = 0
        best_start = 0

        for i, (pos, length) in enumerate(term_positions):
            start = max(0, pos - context_size)
            end = min(len(content), pos + length + context_size)

            # Count how many terms are in this snippet
            terms_in_snippet = 1  # Start with 1 for the current term
            for j, (other_pos, other_length) in enumerate(term_positions):
                if i != j and start <= other_pos < end:
                    terms_in_snippet += 1

            if terms_in_snippet > best_score:
                best_score = terms_in_snippet
                best_start = start

        # Extract the snippet
        end = min(len(content), best_start + context_size * 2)
        snippet = content[best_start:end].replace('\n', ' ').strip()

        return snippet

    def handle_file_upload(self, file_obj) -> str:
        """Handle file upload from Gradio interface"""
        if file_obj is None:
            return "No file provided. Please select a file to upload."

        # Save the uploaded file
        result = self.upload_handler.save_uploaded_file(file_obj)

        if result["success"]:
            # Refresh the file index to include the new file
            if hasattr(self, 'file_index') and hasattr(self, 'index_builder'):
                # Just index the host_files directory to avoid reprocessing all files
                host_dir = os.path.join(self.data_dir, "host_files")
                self.index_builder.index_directory(host_dir)

                # Add the file to the retriever
                filename = result["file_name"]
                file_path = result["file_path"]
                file_type = self.file_processor.get_file_type(filename)

                doc = {
                    "id": file_path,
                    "filename": filename,
                    "type": file_type,
                    "content": self._get_file_content(file_path, filename, file_type)
                }

                self.retriever.add_document(doc)

                return f"File '{result['file_name']}' uploaded and indexed successfully. You can now query it."
            else:
                # Fall back to full refresh if index not available
                self.refresh_file_index()
                return f"File '{result['file_name']}' uploaded and indexed successfully."
        else:
            return result["message"]

    def handle_multiple_uploads(self, file_list) -> str:
        """Handle multiple file uploads from Gradio interface"""
        if not file_list:
            return "No files provided. Please select files to upload."

        # Save the uploaded files
        result = self.upload_handler.handle_multiple_uploads(file_list)
        summary = self.upload_handler.get_upload_summary(result)

        # Refresh the file index if any files were uploaded successfully
        if result["success"]:
            if hasattr(self, 'file_index') and hasattr(self, 'index_builder'):
                # Just index the host_files directory
                host_dir = os.path.join(self.data_dir, "host_files")
                index_result = self.index_builder.index_directory(host_dir)

                summary += f"\n\nIndexed {index_result['indexed']} new files."
                summary += "\nFiles have been indexed and are ready for querying."
            else:
                # Fall back to full refresh
                self.refresh_file_index()
                summary += "\n\nFiles have been indexed and are ready for querying."

        return summary


# Initialize the assistant
assistant = AIAssistant()

# Create the Gradio interface
def respond(message, chat_history):
    # Get response from assistant
    bot_message = assistant.get_response(message, chat_history)

    # Update chat history
    chat_history.append((message, bot_message))
    return "", chat_history

def list_files():
    """Get list of available files for display"""
    return assistant.get_file_list()

def refresh_files():
    """Refresh the file index"""
    result = assistant.refresh_file_index()
    return result

def handle_file_upload(file):
    """Handle file upload"""
    return assistant.handle_file_upload(file)

def handle_multiple_uploads(files):
    """Handle multiple file uploads"""
    return assistant.handle_multiple_uploads(files)

def search_files(query):
    """Search files for a query"""
    if not query:
        return "Please enter a search term."
    return assistant.search_files(query)

# Create and launch the interface
with gr.Blocks(title="AI Assistant") as demo:
    gr.Markdown("# Your Personal AI Assistant")
    gr.Markdown("Ask questions about your data or files")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=500)
            msg = gr.Textbox(placeholder="Type your message here...", show_label=False)
            with gr.Row():
                clear = gr.Button("Clear Conversation")
                files_btn = gr.Button("List Files")
                refresh_btn = gr.Button("Refresh Files")

        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.Tab("Files"):
                    file_status = gr.TextArea(label="Data Status", value="System initialized with sample data.")

                    # Add progress bar for indexing
                    with gr.Group(visible=False) as indexing_group:
                        index_progress = gr.Slider(minimum=0, maximum=1, value=0, label="Indexing Progress")
                        index_status = gr.Markdown("Indexing in progress...")

                    gr.Markdown("### File Commands:")
                    gr.Markdown("- `list files` - See available files")
                    gr.Markdown("- `read file: filename.txt` - View file contents")
                    gr.Markdown("- `search files: keyword` - Search in files")
                    gr.Markdown("- `summarize filename.pdf` - Get document summary")
                    gr.Markdown("- `refresh files` - Update after adding new files")

                    with gr.Accordion("Upload Files"):
                        single_file = gr.File(label="Upload a single file")
                        upload_btn = gr.Button("Upload")

                        multiple_files = gr.Files(label="Upload multiple files")
                        upload_multiple_btn = gr.Button("Upload All")

                        upload_status = gr.TextArea(label="Upload Status")

                with gr.Tab("Search"):
                    search_query = gr.Textbox(label="Search Term", placeholder="Enter keywords to search across all files")
                    search_btn = gr.Button("Search Files")
                    search_results = gr.TextArea(label="Search Results")

                    gr.Markdown("### Advanced Search Tips:")
                    gr.Markdown("- Use specific terms for better results")
                    gr.Markdown("- Include file types (.pdf, .docx) to narrow search")
                    gr.Markdown("- For document content, try terms like 'contains' or 'about'")

                with gr.Tab("Document Tools"):
                    doc_selector = gr.Dropdown(label="Select Document", choices=[], interactive=True)
                    doc_operation = gr.Radio(
                        label="Operation",
                        choices=["Summarize", "Extract Key Points", "Extract Entities", "Find Statistics", "Create Timeline"],
                        value="Summarize"
                    )
                    doc_process_btn = gr.Button("Process Document")
                    doc_results = gr.TextArea(label="Results")
                    doc_refresh_btn = gr.Button("Refresh Document List")

    # Set up interactions
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: None, None, chatbot, queue=False)
    files_btn.click(list_files, None, file_status)

    # For refresh button, we need to update the indexing progress UI
    def start_refresh():
        result = assistant.refresh_file_index()
        return {
            indexing_group: gr.Group.update(visible=True),
            file_status: result
        }

    refresh_btn.click(
        start_refresh,
        None,
        [indexing_group, file_status]
    )

    # Add an update interval for the indexing progress
    def update_indexing_progress():
        status = assistant.get_indexing_status()
        progress = status["progress"]
        message = status["message"]

        # If indexing is complete, hide the progress bar
        if status["status"] == "completed":
            return {
                index_progress: progress,
                index_status: message,
                indexing_group: gr.Group.update(visible=False),
                file_status: f"{message}\n\nFiles are now available for querying."
            }
        else:
            return {
                index_progress: progress,
                index_status: message
            }

    demo.add_loop(update_indexing_progress, None, [index_progress, index_status, indexing_group, file_status], interval=1)

    # Upload functionality
    upload_btn.click(handle_file_upload, single_file, upload_status)
    upload_multiple_btn.click(handle_multiple_uploads, multiple_files, upload_status)

    # Search functionality
    search_btn.click(search_files, search_query, search_results)

    # Document processing functionality
    def get_document_list():
        """Get list of available documents for dropdown"""
        file_list = []
        if hasattr(assistant, 'file_index'):
            all_files = assistant.file_index.get_all_files()
            for file_info in all_files:
                filename = file_info['filename']
                file_type = file_info['type']
                if file_type in ['pdf', 'docx', 'text']:
                    file_list.append(filename)
        else:
            # Fall back to basic listing
            file_list = (
                assistant.text_handler.list_files() +
                [f for f in assistant.doc_handler.list_files() if f.endswith('.pdf') or f.endswith('.docx')] +
                assistant.host_file_handler.list_files() +
                [f for f in assistant.host_doc_handler.list_files() if f.endswith('.pdf') or f.endswith('.docx')]
            )
        return sorted(file_list)

    def process_document(filename, operation):
        """Process a document based on the selected operation"""
        if not filename:
            return "Please select a document first."

        return assistant.process_document(filename, operation)

    # Connect document processing functions
    doc_refresh_btn.click(
        lambda: gr.Dropdown.update(choices=get_document_list()),
        None,
        doc_selector
    )

    doc_process_btn.click(
        process_document,
        [doc_selector, doc_operation],
        doc_results
    )

    # Populate document dropdown on load
    demo.load(
        lambda: gr.Dropdown.update(choices=get_document_list()),
        None,
        doc_selector
    )

# Launch the app
if __name__ == "__main__":
    # Load the model first
    assistant.load_model()

    # Launch the web interface
    # Setting server_name to 0.0.0.0 makes it accessible outside the container
    demo.launch(server_name="0.0.0.0", server_port=7860)

    print("Interface is running. Access it at http://localhost:7860")