"""
File indexing system for AI Assistant.
Maintains an index of files and their content for efficient retrieval.
"""
import os
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from file_handler import TextFileHandler, DocumentHandler, FileProcessor
from file_batch_processor import BatchProcessor

class FileIndexBuilder:
    """Builds and maintains a file index"""
    def __init__(self,
                 index: Optional[FileIndex] = None,
                 processor: Optional[BatchProcessor] = None):
        self.index = index or FileIndex()
        self.processor = processor or BatchProcessor()

    def index_directory(self, directory: str, force_update: bool = False) -> Dict[str, Any]:
        """Index all files in a directory"""
        start_time = time.time()

        # Get all files in the directory
        file_paths = []
        for root, _, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                file_paths.append(file_path)

        # Determine which files need to be indexed
        files_to_index = []
        for file_path in file_paths:
            if force_update or self.index.file_needs_update(file_path):
                files_to_index.append(file_path)

        # Process files that need indexing
        indexed_count = 0
        error_count = 0
        skipped_count = len(file_paths) - len(files_to_index)

        if files_to_index:
            # Create a temporary directory with symlinks to files that need indexing
            temp_dir = "data/temp_index"
            os.makedirs(temp_dir, exist_ok=True)

            # Clear temp directory
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))

            # Create symlinks or copy files
            for file_path in files_to_index:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(temp_dir, filename)

                try:
                    # Try to create a symlink first
                    try:
                        os.symlink(file_path, dest_path)
                    except (OSError, AttributeError):
                        # Fallback to copy
                        import shutil
                        shutil.copy2(file_path, dest_path)
                except Exception as e:
                    print(f"Error linking file {file_path}: {str(e)}")
                    error_count += 1

            # Process the temp directory
            def update_index(job_info):
                if job_info["status"] == "completed" and job_info["result"]:
                    # Get the original file path
                    orig_filename = job_info["filename"]
                    for file_path in files_to_index:
                        if os.path.basename(file_path) == orig_filename:
                            # Add to index
                            self.index.add_file(file_path, job_info["result"])
                            break

            # Process files
            self.processor.process_directory(temp_dir, callback=update_index)

            # Count results
            indexed_count = sum(1 for job in self.processor.jobs if job.status == "completed")
            error_count += sum(1 for job in self.processor.jobs if job.status == "failed")

        # Return summary
        duration = time.time() - start_time
        return {
            "directory": directory,
            "total_files": len(file_paths),
            "indexed": indexed_count,
            "errors": error_count,
            "skipped": skipped_count,
            "duration": duration
        }

    def update_index(self, directories: List[str], force_update: bool = False) -> Dict[str, Any]:
        """Update the index for multiple directories"""
        results = []
        for directory in directories:
            result = self.index_directory(directory, force_update)
            results.append(result)

        # Compute overall statistics
        total_files = sum(r["total_files"] for r in results)
        indexed = sum(r["indexed"] for r in results)
        errors = sum(r["errors"] for r in results)
        skipped = sum(r["skipped"] for r in results)
        duration = sum(r["duration"] for r in results)

        return {
            "directories": len(directories),
            "total_files": total_files,
            "indexed": indexed,
            "errors": errors,
            "skipped": skipped,
            "duration": duration,
            "details": results
        }

class FileIndex:
    """Maintains an index of files and their content"""
    def __init__(self, index_file: str = "data/file_index.json"):
        self.index_file = index_file
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load index from file"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error loading index file: {self.index_file}")
                return self._create_empty_index()
        else:
            return self._create_empty_index()

    def _create_empty_index(self) -> Dict[str, Any]:
        """Create an empty index"""
        return {
            "version": 1,
            "last_updated": time.time(),
            "files": {},
            "directories": {}
        }

    def _save_index(self):
        """Save index to file"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)

        # Update timestamp
        self.index["last_updated"] = time.time()

        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate file hash"""
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
                return hashlib.md5(file_data).hexdigest()
        except:
            # If we can't read the file, use mtime as hash
            return str(os.path.getmtime(file_path))

    def add_file(self, file_path: str, file_info: Dict[str, Any]):
        """Add a file to the index"""
        # Calculate absolute path and file hash
        abs_path = os.path.abspath(file_path)
        file_hash = self._get_file_hash(abs_path)

        # Add directory to index if not present
        directory = os.path.dirname(abs_path)
        if directory not in self.index["directories"]:
            self.index["directories"][directory] = {
                "path": directory,
                "files": []
            }

        # Add file to directory
        if abs_path not in self.index["directories"][directory]["files"]:
            self.index["directories"][directory]["files"].append(abs_path)

        # Add file to index
        self.index["files"][abs_path] = {
            "path": abs_path,
            "filename": os.path.basename(abs_path),
            "hash": file_hash,
            "last_indexed": time.time(),
            "type": file_info.get("type", "unknown"),
            "size": os.path.getsize(abs_path),
            "metadata": file_info.get("metadata", {})
        }

        # Save index
        self._save_index()

    def remove_file(self, file_path: str):
        """Remove a file from the index"""
        abs_path = os.path.abspath(file_path)

        # Remove from files
        if abs_path in self.index["files"]:
            del self.index["files"][abs_path]

        # Remove from directory
        directory = os.path.dirname(abs_path)
        if directory in self.index["directories"]:
            if abs_path in self.index["directories"][directory]["files"]:
                self.index["directories"][directory]["files"].remove(abs_path)

        # Save index
        self._save_index()

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file info from index"""
        abs_path = os.path.abspath(file_path)
        return self.index["files"].get(abs_path)

    def file_needs_update(self, file_path: str) -> bool:
        """Check if file needs to be reindexed"""
        abs_path = os.path.abspath(file_path)

        # Check if file exists in index
        if abs_path not in self.index["files"]:
            return True

        # Check if file has been modified
        file_hash = self._get_file_hash(abs_path)
        stored_hash = self.index["files"][abs_path]["hash"]

        return file_hash != stored_hash

    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all files in the index"""
        return list(self.index["files"].values())

    def get_files_by_type(self, file_type: str) -> List[Dict[str, Any]]:
        """Get files of a specific type"""
        return [
            file_info for file_info in self.index["files"].values()
            if file_info["type"] == file_type
        ]

    def get_files_in_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Get all files in a directory"""
        abs_dir = os.path.abspath(directory)

        if abs_dir not in self.index["directories"]:
            return []

        return [
            self.index["files"][file_path]
            for file_path in self.index["directories"][abs_dir]["files"]
            if file_path in self.index["files"]
        ]

    def clear_index(self):
        """Clear the entire index"""
        self.index = self._create_empty_index()
        self._save_index()

    def get_index_summary(self) -> Dict[str, Any]:
        """Get a summary of the index"""
        # Count files by type
        file_types = {}
        for file_info in self.get_all_files():
            file_type = file_info["type"]
            if file_type not in file_types:
                file_types[file_type] = 0
            file_types[file_type] += 1

        # Get directory stats
        directories = {}
        for dir_path, dir_info in self.index["directories"].items():
            directories[dir_path] = len(dir_info["files"])

        # Compute last update time
        last_updated = self.index["last_updated"]
        last_updated_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_updated))

        return {
            "total_files": len(self.get_all_files()),
            "file_types": file_types,
            "directories": directories,
            "last_updated": last_updated_str
        }