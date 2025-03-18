"""
Logging utilities for State of Mika.
"""

import logging
from typing import Optional

def setup_logging(level: int = logging.INFO, formatter: Optional[logging.Formatter] = None) -> None:
    """
    Set up logging for State of Mika.
    
    Args:
        level: Logging level
        formatter: Custom formatter
    """
    if formatter is None:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("state_of_mika")
    logger.setLevel(level)
    logger.addHandler(handler)
    
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"state_of_mika.{name}")