"""
File batch processor for AI Assistant.
Process multiple files in parallel and extract content for indexing.
"""
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import traceback

from file_handler import TextFileHandler, DocumentHandler, FileProcessor

class FileProcessingJob:
    """Represents a file processing job with progress tracking"""
    def __init__(self, filename: str, file_type: str):
        self.filename = filename
        self.file_type = file_type
        self.status = "pending"  # pending, processing, completed, failed
        self.start_time = None
        self.end_time = None
        self.error = None
        self.result = None

    def start(self):
        """Mark job as started"""
        self.status = "processing"
        self.start_time = time.time()
        return self

    def complete(self, result: Dict[str, Any]):
        """Mark job as completed"""
        self.status = "completed"
        self.end_time = time.time()
        self.result = result
        return self

    def fail(self, error: str):
        """Mark job as failed"""
        self.status = "failed"
        self.end_time = time.time()
        self.error = error
        return self

    def get_duration(self) -> float:
        """Get job duration in seconds"""
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "filename": self.filename,
            "file_type": self.file_type,
            "status": self.status,
            "duration": self.get_duration(),
            "error": self.error,
            "result": self.result
        }

class BatchProcessor:
    """Process multiple files in parallel"""
    def __init__(self,
                 text_handler: TextFileHandler = None,
                 doc_handler: DocumentHandler = None,
                 max_workers: int = 4):
        self.text_handler = text_handler or TextFileHandler()
        self.doc_handler = doc_handler or DocumentHandler()
        self.file_processor = FileProcessor(self.text_handler, self.doc_handler)
        self.max_workers = max_workers
        self.jobs = []
        self.lock = threading.Lock()

    def _get_files_to_process(self, directory: str) -> List[Dict[str, str]]:
        """Get list of files to process in a directory"""
        files = []

        # Set handlers to use the specified directory
        self.text_handler.base_directory = directory
        self.doc_handler.base_directory = directory

        # Get all files in the directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_type = self.file_processor.get_file_type(filename)
                files.append({
                    "filename": filename,
                    "file_type": file_type
                })

        return files

    def _process_file(self, job: FileProcessingJob) -> FileProcessingJob:
        """Process a single file"""
        try:
            job.start()

            filename = job.filename
            file_type = job.file_type

            # Process file based on type
            if file_type == "text":
                content = self.text_handler.read_text(filename)
                result = {"filename": filename, "content": content, "type": "text"}

            elif file_type == "json":
                content = self.text_handler.read_json(filename)
                result = {"filename": filename, "content": content, "type": "json"}

            elif file_type == "csv":
                content = self.text_handler.read_csv(filename)
                result = {"filename": filename, "content": content, "type": "csv"}

            elif file_type == "pdf" and hasattr(self.doc_handler, 'pdf_available') and self.doc_handler.pdf_available:
                content = self.doc_handler.extract_text_from_pdf(filename)
                result = {"filename": filename, "content": content, "type": "pdf"}

            elif file_type == "docx" and hasattr(self.doc_handler, 'docx_available') and self.doc_handler.docx_available:
                content = self.doc_handler.extract_text_from_docx(filename)
                result = {"filename": filename, "content": content, "type": "docx"}

            else:
                return job.fail(f"Unsupported file type: {file_type}")

            # Add metadata to result
            if file_type in ["pdf", "docx"]:
                metadata = self.doc_handler.get_document_metadata(filename)
                result["metadata"] = metadata

            return job.complete(result)
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}\n{traceback.format_exc()}"
            return job.fail(error_msg)

    def process_directory(self, directory: str, callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Process all files in a directory in parallel"""
        # Get files to process
        files = self._get_files_to_process(directory)

        # Create jobs
        self.jobs = [FileProcessingJob(file["filename"], file["file_type"]) for file in files]

        # Process files in parallel
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit jobs
            future_to_job = {executor.submit(self._process_file, job): job for job in self.jobs}

            # Process results as they complete
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    processed_job = future.result()

                    # If job completed successfully, add result to list
                    if processed_job.status == "completed" and processed_job.result:
                        with self.lock:
                            results.append(processed_job.result)

                    # Call callback if provided
                    if callback:
                        callback(processed_job.to_dict())
                except Exception as e:
                    print(f"Error processing job: {str(e)}")
                    # Call callback with error
                    if callback:
                        job.fail(str(e))
                        callback(job.to_dict())

        return results

    def get_progress(self) -> Dict[str, Any]:
        """Get progress information"""
        with self.lock:
            total = len(self.jobs)
            completed = sum(1 for job in self.jobs if job.status == "completed")
            failed = sum(1 for job in self.jobs if job.status == "failed")
            processing = sum(1 for job in self.jobs if job.status == "processing")
            pending = sum(1 for job in self.jobs if job.status == "pending")

            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "pending": pending,
                "progress": (completed + failed) / total if total > 0 else 1.0
            }

    def get_job_status(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        with self.lock:
            for job in self.jobs:
                if job.filename == filename:
                    return job.to_dict()
        return None

    def get_all_job_status(self) -> List[Dict[str, Any]]:
        """Get status of all jobs"""
        with self.lock:
            return [job.to_dict() for job in self.jobs]