"""
File upload handler for AI Assistant.
Provides interfaces to manage file uploads from the Gradio UI.
"""
import os
import shutil
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class FileUploadHandler:
    """Handler for file uploads from the Gradio UI"""
    def __init__(self, upload_dir: str = "data/host_files"):
        self.upload_dir = upload_dir
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)

    def save_uploaded_file(self, file) -> Dict[str, Any]:
        """Save an uploaded file to the upload directory"""
        try:
            if file is None:
                return {
                    "success": False,
                    "message": "No file provided",
                    "file_name": None,
                    "file_path": None
                }

            # Get the file name
            file_name = os.path.basename(file.name)
            file_path = os.path.join(self.upload_dir, file_name)

            # Save the file to the upload directory
            shutil.copy(file.name, file_path)

            return {
                "success": True,
                "message": f"File '{file_name}' uploaded successfully",
                "file_name": file_name,
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error uploading file: {str(e)}",
                "file_name": None,
                "file_path": None
            }

    def handle_multiple_uploads(self, file_list) -> Dict[str, Any]:
        """Handle multiple file uploads"""
        if not file_list:
            return {
                "success": False,
                "message": "No files provided",
                "files": []
            }

        results = []
        for file in file_list:
            result = self.save_uploaded_file(file)
            results.append(result)

        # Check if any files were uploaded successfully
        success = any(result["success"] for result in results)

        return {
            "success": success,
            "message": f"Processed {len(results)} files",
            "files": results
        }

    def get_upload_summary(self, result: Dict[str, Any]) -> str:
        """Get a summary of the upload operation"""
        if not result["success"]:
            return result["message"]

        files = result.get("files", [])
        if not files:
            return "No files were processed"

        successful = [f["file_name"] for f in files if f["success"]]
        failed = [f["file_name"] or "Unknown" for f in files if not f["success"]]

        summary = f"Processed {len(files)} files:\n"

        if successful:
            summary += f"\nSuccessfully uploaded {len(successful)} files:"
            for file in successful:
                summary += f"\n  - {file}"

        if failed:
            summary += f"\n\nFailed to upload {len(failed)} files:"
            for file in failed:
                summary += f"\n  - {file}"

        return summary

    def list_uploaded_files(self) -> List[str]:
        """List all files in the upload directory"""
        try:
            return [f for f in os.listdir(self.upload_dir) if os.path.isfile(os.path.join(self.upload_dir, f))]
        except Exception as e:
            print(f"Error listing uploaded files: {str(e)}")
            return []

    def delete_uploaded_file(self, file_name: str) -> Dict[str, Any]:
        """Delete an uploaded file"""
        try:
            file_path = os.path.join(self.upload_dir, file_name)
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"File '{file_name}' not found"
                }

            os.remove(file_path)
            return {
                "success": True,
                "message": f"File '{file_name}' deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting file: {str(e)}"
            }