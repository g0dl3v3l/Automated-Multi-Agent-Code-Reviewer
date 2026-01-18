"""
Utilities for parsing and processing incoming file uploads.

This module handles reading file content, managing encoding, and creating
SourceFile objects from raw uploads (including future Zip extraction logic).
"""

from typing import List
from werkzeug.datastructures import FileStorage
from src.schemas.common import SourceFile
from src.utils.logger import get_logger

logger = get_logger(__name__)

def read_file_content(file: FileStorage) -> str:
    """
    Reads and decodes the content of an uploaded file.

    Args:
        file (FileStorage): The file object from Flask's request.files.

    Returns:
        str: The decoded text content of the file.

    Raises:
        UnicodeDecodeError: If the file is binary or not UTF-8 encoded.
    """
    try:
        return file.read().decode('utf-8')
    except UnicodeDecodeError:
        logger.warning(f"Failed to decode file: {file.filename}")
        return ""  # Return empty string for binary/unreadable files

def parse_uploaded_files(files: List[FileStorage]) -> List[SourceFile]:
    """
    Converts a list of Flask FileStorage objects into domain SourceFile models.

    Args:
        files (List[FileStorage]): The raw files from the HTTP request.

    Returns:
        List[SourceFile]: A list of validated SourceFile Pydantic objects.
    """
    source_files = []
    
    for file in files:
        if not file.filename:
            continue
            
        content = read_file_content(file)
        if content:
            source_files.append(SourceFile(file_path=file.filename, content=content))
            logger.info(f"Successfully parsed file: {file.filename}")
            
    return source_files