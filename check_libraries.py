"""
Check for required libraries.
This script is used during Docker build to verify dependencies.
"""

# Check for PyPDF
try:
    import pypdf
    print('PyPDF library installed successfully')
except ImportError:
    print('PyPDF library not found')

# Check for Python-docx
try:
    import docx
    print('Python-docx library installed successfully')
except ImportError:
    print('Python-docx library not found')