"""
Simplified run script for AI Assistant.
Use this to start the assistant directly without Docker.
"""

import os
import sys
import argparse
import importlib.util
import webbrowser
from pathlib import Path

def check_dependencies():
    """Check for required dependencies"""
    missing_deps = []

    # Check for gradio
    try:
        import gradio
    except ImportError:
        missing_deps.append("gradio")

    # Check for document processing libraries
    try:
        import pypdf
    except ImportError:
        missing_deps.append("pypdf")

    try:
        import docx
    except ImportError:
        missing_deps.append("python-docx")

    # Return status
    if missing_deps:
        print(f"Warning: Missing dependencies: {', '.join(missing_deps)}")
        print("Some features may not work correctly.")
        print("Install with: pip install " + " ".join(missing_deps))
        return False
    return True

def check_components():
    """Check if required files are present"""
    required_files = [
        "app.py",
        "file_handler.py",
        "retrieval_system.py"
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"Error: Missing required files: {', '.join(missing_files)}")
        return False
    return True

def ensure_directories():
    """Ensure data directories exist"""
    dirs = [
        "data",
        "data/files",
        "data/documents",
        "data/host_files",
        "data/database"
    ]

    for directory in dirs:
        os.makedirs(directory, exist_ok=True)

    # Create host_data directory if it doesn't exist
    if not os.path.exists("host_data"):
        os.makedirs("host_data", exist_ok=True)
        with open("host_data/README.txt", "w") as f:
            f.write("# Host Files Directory\n\n")
            f.write("Place your files in this directory to make them accessible to the AI assistant.\n")

def run_assistant(host="127.0.0.1", port=7860, open_browser=True):
    """Run the assistant"""
    # Import app module dynamically
    spec = importlib.util.spec_from_file_location("app", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    # Initialize the assistant
    if not hasattr(app_module, "assistant"):
        print("Error: app.py doesn't contain an 'assistant' object")
        return False

    # Set UI options for the demo
    if hasattr(app_module, "demo"):
        # Set server options
        app_module.demo.queue()

        # Launch the UI
        print(f"Starting AI Assistant at http://{host}:{port}")
        if open_browser:
            webbrowser.open(f"http://{host}:{port}")

        app_module.demo.launch(
            server_name=host,
            server_port=port,
            share=False,
            prevent_thread_lock=False
        )
        return True
    else:
        print("Error: app.py doesn't contain a 'demo' object")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run AI Assistant without Docker")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run on (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Port to run on (default: 7860)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    print("=== AI Assistant Runner ===")

    # Check components
    if not check_components():
        return 1

    # Check dependencies (warning only)
    check_dependencies()

    # Ensure directories exist
    ensure_directories()

    # Run the assistant
    try:
        run_assistant(args.host, args.port, not args.no_browser)
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except Exception as e:
        print(f"Error running assistant: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())