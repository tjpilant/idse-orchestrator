"""
Logger

Centralized logging for IDSE Orchestrator operations.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(name: str = "idse_orchestrator", log_dir: Optional[Path] = None) -> logging.Logger:
    """
    Set up rotating file logger.

    Args:
        name: Logger name
        log_dir: Directory for log files. Defaults to .idse/logs/

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if log_dir is None:
        log_dir = Path.cwd() / ".idse" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Log file with date
    log_file = log_dir / f"orchestrator-{datetime.now().strftime('%Y%m%d')}.log"

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger
