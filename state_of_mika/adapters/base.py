"""
Base adapter class for framework integration.

This module provides the base class for adapters that connect
AI agent frameworks to MCP capabilities.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("state_of_mika.adapters")

class AgentAdapter(ABC):
    """
    Base class for agent framework adapters.
    
    Adapters handle the integration between AI agent frameworks and MCP.
    They translate between framework-specific concepts and MCP's protocol.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this adapter."""
        pass
    
    @abstractmethod
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this adapter can handle the given object.
        
        Args:
            obj: The object to check
            
        Returns:
            True if this adapter can handle the object, False otherwise
        """
        pass
    
    @abstractmethod
    async def initialize(self, agent: Any) -> None:
        """
        Initialize the adapter with an agent instance.
        
        Args:
            agent: The agent instance
        """
        pass
    
    @abstractmethod
    async def configure_mcp(self, tools: Dict[str, Any]) -> None:
        """
        Configure the adapter with MCP tools.
        
        Args:
            tools: Available MCP tools
        """
        pass
    
    @abstractmethod
    async def handle_tool_response(self, request_id: str, result: Any) -> None:
        """
        Handle a tool response.
        
        Args:
            request_id: The original request ID
            result: The tool execution result
        """
        pass
    
    @abstractmethod
    async def handle_tool_error(self, request_id: str, error: Exception) -> None:
        """
        Handle a tool error.
        
        Args:
            request_id: The original request ID
            error: The error that occurred
        """
        pass
    
    @abstractmethod
    async def dispose(self) -> None:
        """Clean up resources."""
        pass
    
    def __init__(self):
        """Initialize the adapter."""
        self.tool_request_handlers = []
        self.tools = None
        self.pending_requests = {}
    
    def on_tool_request(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a handler for tool requests.
        
        Args:
            handler: Function to call when a tool request is made
        """
        self.tool_request_handlers.append(handler)
    
    async def emit_tool_request(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Emit a tool request to all registered handlers.
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool
            
        Returns:
            The request ID
        """
        request_id = str(uuid.uuid4())
        
        request = {
            "id": request_id,
            "tool_name": tool_name,
            "params": params,
            "adapter": self
        }
        
        for handler in self.tool_request_handlers:
            try:
                await handler(request)
            except Exception as e:
                logger.error(f"Error in tool request handler: {e}")
                await self.handle_tool_error(request_id, e)
                
        return request_id