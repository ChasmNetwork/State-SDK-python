"""
Main Mika class for interacting with MCP servers.

This module provides the core functionality for discovering and
using MCP servers with AI agent frameworks.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from state_of_mika.client.client import MCPClient
from state_of_mika.registry.registry import ServerRegistry
from state_of_mika.adapters.base import AgentAdapter

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

logger = logging.getLogger("state_of_mika")

class Mika:
    """
    Main entry point for State of Mika.
    
    Provides a simple interface for connecting to MCP servers and
    integrating them with AI agent frameworks.
    """
    
    def __init__(self, 
                 registry_url: Optional[str] = None,
                 server_dir: Optional[Path] = None,
                 log_level: int = logging.INFO):
        """
        Initialize a new Mika instance.
        
        Args:
            registry_url: URL to a server registry (optional)
            server_dir: Directory to store server files (optional)
            log_level: Logging level
        """
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Initialize components
        self.registry = ServerRegistry(registry_url, server_dir)
        self.clients = {}  # Maps server_id to MCPClient
        self.adapters = {}  # Maps framework_name to adapter class
        self.connected_agents = {}  # Maps agent instance to adapter
        
        # Register default adapters
        self._register_default_adapters()
        
        logger.info("Mika initialized")
    
    def _register_default_adapters(self):
        """Register the default adapters for common frameworks."""
        try:
            # Import and register adapters if available
            from state_of_mika.adapters.langchain import LangChainAdapter
            self.register_adapter("langchain", LangChainAdapter())
        except ImportError:
            logger.debug("LangChain adapter not available")
            
        try:
            from state_of_mika.adapters.autogpt import AutoGPTAdapter
            self.register_adapter("autogpt", AutoGPTAdapter())
        except ImportError:
            logger.debug("AutoGPT adapter not available")
    
    async def get_tools(self, servers: List[str], 
                       install_missing: bool = True, 
                       local_only: bool = False) -> Dict[str, Any]:
        """
        Get available MCP tools from specified servers.
        
        Args:
            servers: List of server IDs or names
            install_missing: Whether to install missing servers
            local_only: Whether to only use local servers
            
        Returns:
            Dictionary containing server info and available tools
        """
        logger.info(f"Discovering tools from servers: {', '.join(servers)}")
        
        tools = {
            "servers": {},
            "all_tools": []
        }
        
        for server_name in servers:
            try:
                # Get or install server
                server_info = self.registry.get_server(server_name)
                
                if not server_info and install_missing:
                    logger.info(f"Server {server_name} not found, attempting to install...")
                    server_info = await self.registry.install_server(server_name)
                
                if not server_info:
                    logger.warning(f"Server {server_name} not found and installation disabled")
                    continue
                
                # Skip remote servers if local_only is True
                if local_only and server_info["type"] == "remote":
                    logger.warning(f"Skipping remote server {server_name} (local_only=True)")
                    continue
                
                # Connect to server and get tools
                client = await self.get_or_create_client(server_name)
                server_tools = await client.list_tools()
                
                # Store tools in result
                tools["servers"][server_name] = {
                    "info": server_info,
                    "tools": server_tools
                }
                
                # Add to all tools list
                for tool in server_tools:
                    tools["all_tools"].append({
                        **tool,
                        "server": server_name
                    })
                
                logger.info(f"Discovered {len(server_tools)} tools from {server_name}")
            except Exception as e:
                logger.error(f"Error discovering tools from {server_name}: {e}")
                
        return tools
    
    async def connect(self, agent: Any, adapter: Optional[str] = None,
                     servers: Optional[List[str]] = None) -> AgentAdapter:
        """
        Connect an agent to MCP.
        
        Args:
            agent: The agent instance to connect
            adapter: Name of the adapter to use (optional)
            servers: List of server IDs to use (optional)
            
        Returns:
            The configured adapter
        """
        # Determine which adapter to use
        if adapter and adapter in self.adapters:
            adapter_instance = self.adapters[adapter]
        else:
            adapter_instance = self._detect_adapter(agent)
        
        if not adapter_instance:
            raise ValueError("No suitable adapter found for this agent")
        
        # Initialize adapter with agent
        await adapter_instance.initialize(agent)
        
        # Connect to specified servers or use defaults
        server_list = servers or ["brave_search", "filesystem"]
        tools = await self.get_tools(server_list)
        
        # Configure the adapter with available tools
        await adapter_instance.configure_mcp(tools)
        
        # Store connected agent
        self.connected_agents[agent] = adapter_instance
        
        # Subscribe to adapter events
        self._setup_adapter_events(adapter_instance)
        
        logger.info(f"Connected agent to MCP using {adapter_instance.name} adapter")
        return adapter_instance
    
    async def disconnect(self, agent: Any) -> None:
        """
        Disconnect an agent from MCP.
        
        Args:
            agent: The agent to disconnect
        """
        if agent not in self.connected_agents:
            return
            
        adapter = self.connected_agents[agent]
        await adapter.dispose()
        del self.connected_agents[agent]
        logger.info("Agent disconnected from MCP")
    
    def register_adapter(self, name: str, adapter: AgentAdapter) -> None:
        """
        Register a custom adapter.
        
        Args:
            name: Unique adapter name
            adapter: The adapter instance
        """
        self.adapters[name] = adapter
        logger.info(f"Registered adapter: {name}")
    
    async def add_server(self, server_info: Dict[str, Any]) -> None:
        """
        Add a new MCP server to the registry.
        
        Args:
            server_info: Server information
        """
        await self.registry.add_server(server_info)
        logger.info(f"Added server: {server_info['name']}")
    
    async def connect_to_server(self, server_spec: Union[str, Dict[str, Any]]) -> MCPClient:
        """
        Connect to a specific MCP server directly.
        
        This allows connecting to a server without adding it to the registry first.
        Useful for temporary connections or development servers.
        
        Args:
            server_spec: Server specification (path, URL, or info dict)
            
        Returns:
            Connected MCPClient
        """
        # Handle string inputs (file paths, URLs, or npm packages)
        if isinstance(server_spec, str):
            # Check if it's a URL
            if server_spec.startswith('http://') or server_spec.startswith('https://'):
                server_spec = {
                    "id": f"custom-{hash(server_spec)}",
                    "name": "Custom Server",
                    "description": "Custom server specified by URL",
                    "type": "remote",
                    "url": server_spec
                }
            # Check if it's a file path
            elif server_spec.endswith('.py') or server_spec.endswith('.js'):
                command = 'python' if server_spec.endswith('.py') else 'node'
                server_spec = {
                    "id": f"custom-{hash(server_spec)}",
                    "name": "Custom Server",
                    "description": "Custom server specified by file path",
                    "type": "local",
                    "command": command,
                    "args": [server_spec]
                }
            # Assume it's an npm package
            else:
                server_spec = {
                    "id": f"custom-{hash(server_spec)}",
                    "name": "Custom Server",
                    "description": "Custom server specified by package name",
                    "type": "local",
                    "command": "npx",
                    "args": [server_spec]
                }

        # Create and connect a client
        client_id = f"custom-{server_spec['id']}"
        client = MCPClient(server_spec)
        await client.connect()

        # Store client for reuse
        self.clients[client_id] = client
        
        return client
    
    async def get_or_create_client(self, server_name: str) -> MCPClient:
        """
        Get or create a client for a server.
        
        Args:
            server_name: Server ID or name
        
        Returns:
            Connected MCPClient
        """
        if server_name in self.clients:
            return self.clients[server_name]
        
        server_info = self.registry.get_server(server_name)
        if not server_info:
            raise ValueError(f"Server not found: {server_name}")
        
        client = MCPClient(server_info)
        await client.connect()
        
        self.clients[server_name] = client
        return client
    
    def _detect_adapter(self, agent: Any) -> Optional[AgentAdapter]:
        """
        Detect which adapter to use for an agent.
        
        Args:
            agent: The agent to detect
            
        Returns:
            Suitable adapter or None
        """
        for adapter in self.adapters.values():
            if adapter.can_handle(agent):
                return adapter
        
        return None
    
    def _setup_adapter_events(self, adapter: AgentAdapter) -> None:
        """
        Set up event handling for an adapter.
        
        Args:
            adapter: The adapter to set up
        """
        adapter.on_tool_request(self._handle_tool_request)
    
    async def _handle_tool_request(self, request: Dict[str, Any]) -> None:
        """
        Handle a tool request from an adapter.
        
        Args:
            request: The tool request
        """
        try:
            # Find the appropriate server for this tool
            tool_name = request["tool_name"]
            params = request["params"]
            request_id = request["id"]
            adapter = request["adapter"]
            
            # Find server for tool
            server_name = None
            for s_name, s_info in adapter.tools["servers"].items():
                for tool in s_info["tools"]:
                    if tool["name"] == tool_name:
                        server_name = s_name
                        break
                if server_name:
                    break
            
            if not server_name:
                raise ValueError(f"No server found for tool: {tool_name}")
            
            # Get client and call tool
            client = await self.get_or_create_client(server_name)
            result = await client.call_tool(tool_name, params)
            
            # Send result back to adapter
            await adapter.handle_tool_response(request_id, result)
        except Exception as e:
            logger.error(f"Error handling tool request: {e}")
            if adapter and request_id:
                await adapter.handle_tool_error(request_id, e)