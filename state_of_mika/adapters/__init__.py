"""
Adapters module for State of Mika SDK

This package provides adapters for interpreting natural language
requests and interfacing with MCP servers.
"""

__all__ = []

from typing import Dict, List, Any, Optional

class BaseAdapter:
    """
    Base class for LLM adapters.
    
    All LLM-specific adapters should inherit from this class.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        pass
    
    async def setup(self) -> None:
        """Set up the adapter."""
        pass
    
    async def process_request(self, request: str) -> Dict[str, Any]:
        """
        Process a natural language request from an LLM.
        
        Args:
            request: The natural language request from the LLM
            
        Returns:
            Response to be sent back to the LLM
        """
        raise NotImplementedError("Subclasses must implement process_request method") 