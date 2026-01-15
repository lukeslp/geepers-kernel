"""
File Utilities
Common file and directory operations for use across projects.

Extracted from file_info.py for reusability.
"""

import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List


logger = logging.getLogger(__name__)


def format_size(bytes_size: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.23 MB")

    Examples:
        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1536000)
        '1.46 MB'
    """
    size = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_timestamp(timestamp: float) -> str:
    """
    Format Unix timestamp to readable date string.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        Formatted date string (YYYY-MM-DD HH:MM:SS)

    Examples:
        >>> format_timestamp(1609459200)
        '2021-01-01 00:00:00'
    """
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def calculate_hash(
    filepath: str,
    algorithm: str = 'sha256',
    chunk_size: int = 4096
) -> str:
    """
    Calculate file hash using specified algorithm.

    Args:
        filepath: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        chunk_size: Size of chunks to read (default: 4096 bytes)

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If algorithm is not supported
        FileNotFoundError: If file doesn't exist
        Exception: For other file read errors

    Examples:
        >>> calculate_hash('example.txt')  # doctest: +SKIP
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    try:
        hash_func = getattr(hashlib, algorithm)()
    except AttributeError:
        raise ValueError(
            f"Unsupported hash algorithm: {algorithm}. "
            f"Use one of: md5, sha1, sha256, sha512"
        )

    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error calculating hash for {filepath}: {e}")
        raise


def get_file_type(filepath: str) -> str:
    """
    Get file type category based on extension.

    Args:
        filepath: Path to file

    Returns:
        File type category string

    Examples:
        >>> get_file_type('document.pdf')
        'Document file'
        >>> get_file_type('image.jpg')
        'Image file'
        >>> get_file_type('script.py')
        'Code file'
    """
    path = Path(filepath)
    suffix = path.suffix.lower()

    # Common file type categories
    categories = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.heic', '.heif'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
        'document': ['.pdf', '.doc', '.docx', '.odt', '.txt', '.rtf'],
        'spreadsheet': ['.xls', '.xlsx', '.ods', '.csv'],
        'presentation': ['.ppt', '.pptx', '.odp'],
        'archive': ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar'],
        'code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.html', '.css', '.php', '.rb', '.go', '.rs'],
        'data': ['.json', '.xml', '.yaml', '.yml', '.toml', '.ini'],
    }

    for category, extensions in categories.items():
        if suffix in extensions:
            return f"{category.capitalize()} file"

    return "Unknown type" if suffix else "No extension"


def get_file_info(
    filepath: str,
    include_hash: bool = False,
    hash_algorithm: str = 'sha256'
) -> Dict:
    """
    Get comprehensive file information.

    Args:
        filepath: Path to file
        include_hash: Whether to calculate file hash (default: False)
        hash_algorithm: Hash algorithm to use (default: sha256)

    Returns:
        Dictionary containing file metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: For other file stat errors

    Example:
        >>> info = get_file_info('example.txt')  # doctest: +SKIP
        >>> info['size_formatted']  # doctest: +SKIP
        '1.23 KB'
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        stat = path.stat()

        info = {
            'name': path.name,
            'path': str(path.absolute()),
            'type': get_file_type(filepath),
            'size': stat.st_size,
            'size_formatted': format_size(stat.st_size),
            'created': format_timestamp(stat.st_ctime),
            'modified': format_timestamp(stat.st_mtime),
            'accessed': format_timestamp(stat.st_atime),
            'permissions': oct(stat.st_mode)[-3:],
            'is_file': path.is_file(),
            'is_dir': path.is_dir(),
            'is_symlink': path.is_symlink(),
            'extension': path.suffix,
        }

        if include_hash and path.is_file():
            info['hash'] = calculate_hash(filepath, hash_algorithm)
            info['hash_algorithm'] = hash_algorithm

        logger.debug(f"Got file info for {filepath}")
        return info

    except Exception as e:
        logger.error(f"Error getting file info for {filepath}: {e}")
        raise


def get_directory_info(dirpath: str, recursive: bool = True) -> Dict:
    """
    Get directory statistics and file type breakdown.

    Args:
        dirpath: Path to directory
        recursive: Whether to recursively scan subdirectories (default: True)

    Returns:
        Dictionary containing directory statistics

    Raises:
        FileNotFoundError: If directory doesn't exist
        ValueError: If path is not a directory
        Exception: For other errors

    Example:
        >>> info = get_directory_info('/path/to/dir')  # doctest: +SKIP
        >>> info['file_count']  # doctest: +SKIP
        42
    """
    path = Path(dirpath)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {dirpath}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {dirpath}")

    try:
        total_size = 0
        file_count = 0
        dir_count = 0
        file_types = {}

        # Use rglob for recursive, iterdir for non-recursive
        items = path.rglob('*') if recursive else path.iterdir()

        for item in items:
            if item.is_file():
                file_count += 1
                total_size += item.stat().st_size
                ext = item.suffix.lower() or 'no_extension'
                file_types[ext] = file_types.get(ext, 0) + 1
            elif item.is_dir() and recursive:
                dir_count += 1

        info = {
            'name': path.name,
            'path': str(path.absolute()),
            'total_size': total_size,
            'total_size_formatted': format_size(total_size),
            'file_count': file_count,
            'dir_count': dir_count,
            'file_types': file_types,
        }

        logger.debug(f"Got directory info for {dirpath}")
        return info

    except Exception as e:
        logger.error(f"Error getting directory info for {dirpath}: {e}")
        raise


def find_files_by_extension(
    dirpath: str,
    extension: str,
    recursive: bool = True
) -> List[Path]:
    """
    Find all files with a specific extension in a directory.

    Args:
        dirpath: Path to directory
        extension: File extension (with or without leading dot)
        recursive: Whether to search subdirectories (default: True)

    Returns:
        List of Path objects

    Example:
        >>> files = find_files_by_extension('/path/to/dir', '.py')  # doctest: +SKIP
        >>> len(files)  # doctest: +SKIP
        15
    """
    path = Path(dirpath)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {dirpath}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {dirpath}")

    # Ensure extension has leading dot
    if not extension.startswith('.'):
        extension = f'.{extension}'

    pattern = f'**/*{extension}' if recursive else f'*{extension}'

    try:
        files = list(path.glob(pattern))
        logger.debug(f"Found {len(files)} {extension} files in {dirpath}")
        return files
    except Exception as e:
        logger.error(f"Error finding files in {dirpath}: {e}")
        raise


def get_file_age_days(filepath: str) -> float:
    """
    Get file age in days since last modification.

    Args:
        filepath: Path to file

    Returns:
        Age in days (float)

    Example:
        >>> age = get_file_age_days('old_file.txt')  # doctest: +SKIP
        >>> age > 30  # doctest: +SKIP
        True
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    stat = path.stat()
    age_seconds = datetime.now().timestamp() - stat.st_mtime
    age_days = age_seconds / 86400  # seconds in a day

    return age_days


def ensure_directory(dirpath: str) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        dirpath: Path to directory

    Returns:
        Path object

    Example:
        >>> path = ensure_directory('/tmp/test_dir')  # doctest: +SKIP
        >>> path.exists()  # doctest: +SKIP
        True
    """
    path = Path(dirpath)
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory exists: {dirpath}")
    return path


def safe_filename(filename: str, replacement: str = '_') -> str:
    """
    Create a safe filename by removing/replacing problematic characters.

    Args:
        filename: Original filename
        replacement: Character to use for replacement (default: '_')

    Returns:
        Safe filename string

    Example:
        >>> safe_filename('my/file:name?.txt')
        'my_file_name_.txt'
    """
    # Characters that are problematic in filenames
    unsafe_chars = '<>:"/\\|?*'

    safe = filename
    for char in unsafe_chars:
        safe = safe.replace(char, replacement)

    # Remove any control characters
    safe = ''.join(c for c in safe if ord(c) >= 32)

    # Prevent multiple consecutive replacement characters
    while replacement * 2 in safe:
        safe = safe.replace(replacement * 2, replacement)

    return safe.strip(replacement)
