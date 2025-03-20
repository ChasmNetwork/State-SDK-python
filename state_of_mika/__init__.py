"""
State of Mika SDK - AI capability routing system.

This package provides an AI-powered system for:
1. Analyzing natural language requests using Mika
2. Identifying required capabilities and tools
3. Locating, installing, and connecting to appropriate capability servers
4. Returning structured responses or helpful error suggestions
"""

import logging
import os

# Configure the logger for better visibility in presentations
logging.basicConfig(
    level=os.environ.get("SOM_LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

__version__ = "0.2.0"

# Expose the main classes
from .connector import Connector
from .registry import Registry
from .installer import Installer
from .mika_adapter import MikaAdapter
from .som_agent import SoMAgent

# Convenience exports
__all__ = [
    "Connector",
    "Registry", 
    "Installer",
    "MikaAdapter",
    "SoMAgent"
] 