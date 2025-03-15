"""
Setup script for AI Assistant.
Handles initial setup and configuration.
"""
import os
import sys
import shutil
from pathlib import Path
import argparse

def create_directory_structure():
    """Create the necessary directory structure"""
    print("Creating directory structure...")

    # Create main directories
    directories = [
        "data",
        "data/files",
        "data/documents",
        "data/host_files",
        "data/database"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  - Created directory: {directory}")

    return True

def create_env_file():
    """Create a default .env file if it doesn't exist"""
    env_path = ".env"

    if os.path.exists(env_path):
        print(f".env file already exists at {env_path}")
        return False

    print("Creating default .env file...")

    with open(env_path, "w") as f:
        f.write("# AI Assistant Configuration\n\n")
        f.write("# Directory for host files\n")
        f.write("HOST_DATA_DIR=./host_data\n\n")
        f.write("# Model configuration\n")
        f.write("MODEL_TYPE=dummy\n")
        f.write("MODEL_NAME=gpt2\n")
        f.write("MODEL_DEVICE=cpu\n\n")
        f.write("# API keys (uncomment and add your keys if using API-based models)\n")
        f.write("# OPENAI_API_KEY=your-api-key-here\n")
        f.write("# ANTHROPIC_API_KEY=your-api-key-here\n")

    print(f"  - Created .env file at {env_path}")
    return True

def create_sample_files():
    """Create sample files for testing"""
    print("Creating sample files...")

    # Sample text file
    with open("data/files/sample_info.txt", "w") as f:
        f.write("This is a sample text file that contains information about AI assistants.\n")
        f.write("AI assistants can help with various tasks including answering questions, ")
        f.write("searching databases, and analyzing documents.")
    print("  - Created sample_info.txt")

    # Sample JSON file
    import json
    sample_json = {
        "products": [
            {"id": 1, "name": "Product A", "price": 99.99, "category": "Electronics"},
            {"id": 2, "name": "Product B", "price": 49.99, "category": "Books"},
            {"id": 3, "name": "Product C", "price": 149.99, "category": "Electronics"}
        ]
    }
    with open("data/files/products.json", "w") as f:
        json.dump(sample_json, f, indent=2)
    print("  - Created products.json")

    # Sample CSV file
    import csv
    with open("data/files/sales.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "customer", "amount"])
        writer.writerow(["2023-01-01", "Customer A", "125.50"])
        writer.writerow(["2023-01-02", "Customer B", "89.99"])
        writer.writerow(["2023-01-03", "Customer A", "45.00"])
    print("  - Created sales.csv")

    # Create README for host_files
    with open("data/host_files/README.txt", "w") as f:
        f.write("# Host Files Directory\n\n")
        f.write("Place your files in this directory to make them accessible to the AI assistant.\n\n")
        f.write("Supported file types:\n")
        f.write("- Text files (.txt)\n")
        f.write("- PDF documents (.pdf)\n")
        f.write("- Word documents (.docx)\n")
        f.write("- JSON files (.json)\n")
        f.write("- CSV files (.csv)\n\n")
        f.write("After adding files, use the 'refresh files' command in the assistant.")
    print("  - Created README.txt in host_files directory")

    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")

    try:
        import gradio
        print("  ✓ Gradio is installed")
    except ImportError:
        print("  ✗ Gradio is not installed. Install with: pip install gradio")

    try:
        import pypdf
        print("  ✓ PyPDF is installed")
    except ImportError:
        print("  ✗ PyPDF is not installed. Install with: pip install pypdf")

    try:
        import docx
        print("  ✓ Python-docx is installed")
    except ImportError:
        print("  ✗ Python-docx is not installed. Install with: pip install python-docx")

    print("\nNote: Missing dependencies will be installed when running with Docker.")

    return True

def main():
    parser = argparse.ArgumentParser(description="Setup AI Assistant")
    parser.add_argument("--docker", action="store_true", help="Setup for Docker environment")
    parser.add_argument("--local", action="store_true", help="Setup for local environment")
    args = parser.parse_args()

    print("Setting up AI Assistant...")

    # Create directory structure
    create_directory_structure()

    # Create .env file
    create_env_file()

    # Create sample files
    create_sample_files()

    if args.local:
        # Check dependencies for local setup
        check_dependencies()
        print("\nLocal setup completed! You can now run the assistant with 'python app.py'")
    else:
        # Docker is the default
        print("\nSetup completed! You can now run the assistant with 'docker-compose up --build'")
        print("Or use the start.sh script: './start.sh'")

    return 0

if __name__ == "__main__":
    sys.exit(main())