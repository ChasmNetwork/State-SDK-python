"""
LangChain adapter for MCP integration.

This module provides an adapter that connects LangChain agents
to MCP capabilities by registering tools that route to MCP servers.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Callable

from state_of_mika.adapters.base import AgentAdapter

try:
    from langchain.tools import BaseTool
    from langchain.agents import AgentExecutor
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Create dummy classes for type hints
    class BaseTool:
        pass
    class AgentExecutor:
        pass

logger = logging.getLogger("state_of_mika.adapters.langchain")

class MCPTool(BaseTool):
    """Tool that routes requests to an MCP server."""
    
    def __init__(self, name: str, description: str, adapter, tool_name: str):
        """
        Initialize the tool.
        
        Args:
            name: Tool name
            description: Tool description
            adapter: The adapter instance
            tool_name: MCP tool name
        """
        self.adapter = adapter
        self.mcp_tool_name = tool_name
        self.pending_requests = {}
        
        super().__init__(
            name=name,
            description=description,
            return_direct=False
        )
    
    def _run(self, *args, **kwargs):
        """
        Run the tool.
        
        This is a synchronous wrapper around the async _arun method.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(*args, **kwargs))
    
    async def _arun(self, **kwargs):
        """
        Run the tool asynchronously.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool result
        """
        # Create future for result
        request_id = await self.adapter.emit_tool_request(
            self.mcp_tool_name,
            kwargs
        )
        
        # Wait for result
        future = asyncio.Future()
        self.adapter.pending_requests[request_id] = future
        
        try:
            return await future
        finally:
            if request_id in self.adapter.pending_requests:
                del self.adapter.pending_requests[request_id]


class LangChainAdapter(AgentAdapter):
    """Adapter for LangChain agents."""
    
    @property
    def name(self) -> str:
        """Get the name of this adapter."""
        return "langchain"
    
    def __init__(self):
        """Initialize the adapter."""
        super().__init__()
        self.agent = None
        self.pending_requests = {}
        
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available. Install with 'pip install langchain'")
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this adapter can handle the given object.
        
        Args:
            obj: The object to check
            
        Returns:
            True if this adapter can handle the object, False otherwise
        """
        if not LANGCHAIN_AVAILABLE:
            return False
            
        # Check if it's a LangChain AgentExecutor
        return isinstance(obj, AgentExecutor)
    
    async def initialize(self, agent: Any) -> None:
        """
        Initialize the adapter with a LangChain agent.
        
        Args:
            agent: The agent instance
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available. Install with 'pip install langchain'")
            
        if not isinstance(agent, AgentExecutor):
            raise TypeError("Agent must be a LangChain AgentExecutor")
            
        self.agent = agent
        logger.info("LangChain adapter initialized")
    
    async def configure_mcp(self, tools: Dict[str, Any]) -> None:
        """
        Configure the adapter with MCP tools.
        
        Args:
            tools: Available MCP tools
        """
        if not self.agent:
            raise RuntimeError("Adapter not initialized")
            
        self.tools = tools
        
        # Create LangChain tools for each MCP tool
        langchain_tools = []
        
        for tool in tools["all_tools"]:
            # Create tool
            lc_tool = MCPTool(
                name=tool["name"],
                description=tool["description"],
                adapter=self,
                tool_name=tool["name"]
            )
            
            langchain_tools.append(lc_tool)
            
        # Add tools to agent
        self.agent.tools.extend(langchain_tools)
        
        logger.info(f"Added {len(langchain_tools)} MCP tools to LangChain agent")
    
    async def handle_tool_response(self, request_id: str, result: Any) -> None:
        """
        Handle a tool response.
        
        Args:
            request_id: The original request ID
            result: The tool execution result
        """
        future = self.pending_requests.get(request_id)
        if not future:
            logger.warning(f"Received response for unknown request: {request_id}")
            return
            
        if not future.done():
            future.set_result(result)
    
    async def handle_tool_error(self, request_id: str, error: Exception) -> None:
        """
        Handle a tool error.
        
        Args:
            request_id: The original request ID
            error: The error that occurred
        """
        future = self.pending_requests.get(request_id)
        if not future:
            logger.warning(f"Received error for unknown request: {request_id}")
            return
            
        if not future.done():
            future.set_exception(error)
    
    async def dispose(self) -> None:
        """Clean up resources."""
        # Reject all pending requests
        for request_id, future in self.pending_requests.items():
            if not future.done():
                future.set_exception(RuntimeError("Adapter disposed"))
                
        self.pending_requests = {}
        
        # Remove MCP tools from agent
        if self.agent:
            # Filter out MCPTool instances
            self.agent.tools = [t for t in self.agent.tools if not isinstance(t, MCPTool)]
            
        self.agent = None
        logger.info("LangChain adapter disposed")