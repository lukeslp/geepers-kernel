"""
Structured logging configuration for Monarch Money CLI.

Uses loguru for clean, structured logging with rotation and filtering.
"""

import sys
from pathlib import Path
from loguru import logger

# Remove default logger
logger.remove()

# Create logs directory
LOG_DIR = Path.home() / ".mm" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Add console logger (INFO and above)
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Add file logger with rotation (DEBUG and above)
logger.add(
    LOG_DIR / "monarchmoney_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 day",
    retention="30 days",
    compression="gz",
)

# Export configured logger
__all__ = ["logger"]
