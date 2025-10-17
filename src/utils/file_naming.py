#!/usr/bin/env python3
"""
Utility functions for file naming with timestamps and version numbers
"""

from datetime import datetime
from pathlib import Path
import os


def generate_timestamped_filename(base_name: str, extension: str, version: int = 1) -> str:
    """
    Generate a filename with timestamp and version number.
    
    Args:
        base_name: Base name for the file (without extension)
        extension: File extension (e.g., 'xlsx', 'csv', 'pdf')
        version: Version number (default: 1)
    
    Returns:
        Formatted filename: base_name_YYYYMMDD_HHMMSS_vX.extension
    
    Examples:
        >>> generate_timestamped_filename("battery_simulation", "xlsx", 1)
        "battery_simulation_20241220_143022_v1.xlsx"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}_v{version}.{extension}"


def get_next_version_number(directory: Path, base_name: str, extension: str) -> int:
    """
    Get the next version number for a file in a directory.
    
    Args:
        directory: Directory to search for existing files
        base_name: Base name to search for
        extension: File extension to search for
    
    Returns:
        Next version number to use
    """
    if not directory.exists():
        return 1
    
    # Look for existing files with the same base name and extension
    pattern = f"{base_name}_*_v*.{extension}"
    existing_files = list(directory.glob(pattern))
    
    if not existing_files:
        return 1
    
    # Extract version numbers from existing files
    versions = []
    for file in existing_files:
        try:
            # Extract version number from filename
            # Format: base_name_YYYYMMDD_HHMMSS_vX.extension
            parts = file.stem.split('_')
            if len(parts) >= 3 and parts[-1].startswith('v'):
                version = int(parts[-1][1:])  # Remove 'v' prefix
                versions.append(version)
        except (ValueError, IndexError):
            continue
    
    return max(versions) + 1 if versions else 1


def create_timestamped_file(base_name: str, extension: str, directory: Path = None, version: int = None) -> Path:
    """
    Create a timestamped file path with automatic version numbering.
    
    Args:
        base_name: Base name for the file
        extension: File extension
        directory: Directory to save the file (default: current directory)
        version: Specific version number (if None, auto-increment)
    
    Returns:
        Path object for the new file
    """
    if directory is None:
        directory = Path.cwd()
    
    if version is None:
        version = get_next_version_number(directory, base_name, extension)
    
    filename = generate_timestamped_filename(base_name, extension, version)
    return directory / filename


def ensure_output_directory(base_path: Path) -> Path:
    """
    Ensure the output directory exists and create it if necessary.
    
    Args:
        base_path: Base path for the output directory
    
    Returns:
        Path object for the output directory
    """
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path
