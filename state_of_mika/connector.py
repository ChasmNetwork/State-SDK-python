"""
Connector module for bridging LLMs with MCP servers.

This module provides the primary interface for connecting Language Models
with MCP servers.
"""

import os
import sys
import json
import asyncio
import logging
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, AsyncIterator, AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from asyncio import create_task

# Import from mcp package
# This package is installed when a server is installed, so it might not be available
# during import, but will be available when needed
HAS_MCP = False

from .registry import Registry
from .installer import Installer

logger = logging.getLogger(__name__)

class Connector:
    """
    Connector for bridging LLMs with MCP servers.
    
    This class provides the main interface for:
    1. Finding the right MCP server for a capability
    2. Installing the server if needed
    3. Connecting to the server
    4. Executing tools and returning results
    """
    
    def __init__(self, 
                registry: Optional[Registry] = None,
                installer: Optional[Installer] = None):
        """
        Initialize the Connector.
        
        Args:
            registry: Registry for MCP servers (created if None)
            installer: Installer for MCP servers (created if None)
        """
        self.registry = registry or Registry()
        self.installer = installer or Installer(self.registry)
        
        # Dictionary to store active connections
        self.connections: Dict[str, Any] = {}
        
        # Exit stack for proper resource management
        self.exit_stack = AsyncExitStack()
    
    async def setup(self) -> None:
        """Set up the connector by ensuring registry is updated."""
        await self.registry.update()
        
        # Check if MCP package is installed
        if not HAS_MCP:
            logger.warning("MCP package not installed. Will install when needed.")
    
    @asynccontextmanager
    async def connect_session(self, capability: str) -> AsyncIterator[Tuple[str, Any]]:
        """
        Context manager for connecting to a server with the given capability.
        Provides automatic cleanup when the context exits.
        
        Args:
            capability: The capability needed (e.g., "weather", "search")
            
        Yields:
            Tuple of (server_name, connected client)
            
        Raises:
            ValueError: If no suitable server found or connection failed
        """
        server_name, client = None, None
        try:
            server_name, client = await self.find_and_connect(capability)
            yield server_name, client
        finally:
            if server_name:
                await self.disconnect(server_name)
    
    async def find_and_connect(self, capability: str) -> Tuple[str, Any]:
        """
        Find the best server for a capability, install if needed, and connect.
        
        Args:
            capability: The capability needed (e.g., "weather", "search")
            
        Returns:
            Tuple of (server_name, connected client)
            
        Raises:
            ValueError: If no suitable server found or connection failed
        """
        # Find the best server for this capability
        matches = self.registry.search_by_capability(capability)
        
        if not matches:
            raise ValueError(f"No MCP server found for capability: {capability}")
        
        # Try each server in order of relevance
        for server_data in matches:
            server_name = server_data['name']
            
            # Check if already connected
            if server_name in self.connections:
                logger.info(f"Using existing connection to {server_name}")
                return server_name, self.connections[server_name]
            
            # Try to connect to this server
            try:
                client = await self.connect_to_server(server_name)
                return server_name, client
            except Exception as e:
                logger.warning(f"Failed to connect to {server_name}: {e}")
                continue
        
        # If we get here, all connection attempts failed
        raise ValueError(f"Failed to connect to any server for capability: {capability}")
    
    async def connect_to_server(self, server_name: str) -> 'ClientSession':
        """
        Connect to a server by name
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            ClientSession object for interacting with the server
        """
        # First, make sure we have the MCP package imported
        global HAS_MCP
        
        # Import MCP modules here in the function scope
        try:
            import mcp
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            HAS_MCP = True
        except ImportError:
            # Need to install the MCP package
            logger.info("Installing MCP package...")
            await self.installer.install_server({
                "name": "mcp",
                "installation": {'type': 'pip', 'package': 'mcp'}
            })
            
            # Try to import again after installation
            try:
                import mcp
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
                HAS_MCP = True
            except ImportError:
                raise RuntimeError("Failed to install MCP package")
        
        # Get server data
        server_data = self.registry.get_server_by_name(server_name)
        
        if not server_data:
            raise ValueError(f"Server not found in registry: {server_name}")
        
        # Check if already connected
        if server_name in self.connections:
            return self.connections[server_name]
            
        # Check if the server is installed
        installed = self.registry.is_server_installed(server_name)
        
        if not installed:
            # Need to install the server
            logger.info(f"Installing server: {server_name}")
            
            # Get installation information from server data
            installation_info = server_data.get('installation', {})
            
            # Install the server
            server_install_data = {
                "name": server_name,
                "installation": installation_info
            }
            success = await self.installer.install_server(server_install_data)
            if not success:
                raise RuntimeError(f"Failed to install server: {server_name}")
        
        # Now start and connect to the server
        try:
            # Get the command and args to start the server
            command, args, env = self._get_server_launch_info(server_name, server_data)
            
            # Get installation type for potential fallback
            installation_info = server_data.get('installation', {})
            install_type = installation_info.get('type', 'pip')
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            logger.info(f"Starting server: {server_name} with command: {command} {' '.join(args)}")
            
            # Create the client session using the MCP client SDK
            # Add it to our exit stack for proper cleanup
            try:
                read_stream, write_stream = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                
                # Initialize the session
                await session.initialize()
                
                # Store the connection
                self.connections[server_name] = session
                
                logger.info(f"Connected to server: {server_name}")
                return session
            except Exception as launch_error:
                logger.warning(f"Error launching server with primary method: {launch_error}")
                
                # If the standard module approach failed and this is a pip package,
                # try the fallback script approach that uses dynamic imports
                if "-m" in args and install_type == "pip":
                    logger.info(f"Trying alternative launch method for {server_name}")
                    
                    script = (
                        f"import sys; "
                        f"try: "
                        f"    import {server_name}; "
                        f"    if hasattr({server_name}, 'run_server'): "
                        f"        {server_name}.run_server(); "
                        f"    elif hasattr({server_name}, 'main'): "
                        f"        {server_name}.main(); "
                        f"    elif hasattr({server_name}, 'start'): "
                        f"        {server_name}.start(); "
                        f"    else: "
                        f"        sys.exit('Cannot find entry point for {server_name}'); "
                        f"except Exception as e: "
                        f"    sys.exit(f'Error starting {server_name}: {{e}}'); "
                    )
                    
                    fallback_params = StdioServerParameters(
                        command='python',
                        args=['-c', script],
                        env=env
                    )
                    
                    try:
                        logger.info(f"Trying fallback launch method: python -c '{script}'")
                        read_stream, write_stream = await self.exit_stack.enter_async_context(
                            stdio_client(fallback_params)
                        )
                        
                        session = await self.exit_stack.enter_async_context(
                            ClientSession(read_stream, write_stream)
                        )
                        
                        # Initialize the session
                        await session.initialize()
                        
                        # Store the connection
                        self.connections[server_name] = session
                        
                        logger.info(f"Connected to server using fallback method: {server_name}")
                        return session
                    except Exception as fallback_error:
                        logger.error(f"Fallback launch also failed: {fallback_error}")
                        raise RuntimeError(f"Could not launch server {server_name} using any method")
                else:
                    # Re-raise the original error if we can't try a fallback
                    raise
                
        except Exception as e:
            logger.error(f"Failed to connect to server {server_name}: {e}")
            raise
    
    def _get_server_launch_info(self, server_name: str, server_data: Dict[str, Any]) -> Tuple[str, List[str], Dict[str, str]]:
        """
        Get the command, args, and environment variables to launch a server.
        
        Args:
            server_name: Name of the server
            server_data: Server data from the registry
            
        Returns:
            Tuple of (command, args, env)
        """
        # Get installation information
        installation_info = server_data.get('installation', {})
        
        # Check if there are explicit launch instructions in the server data
        launch_config = server_data.get('launch', {})
        if launch_config:
            command = launch_config.get('command')
            args = launch_config.get('args', [])
            env_overrides = launch_config.get('env', {})
            
            # Combine with default environment
            env = os.environ.copy()
            
            # Process environment variables, substituting ${VAR} references
            processed_env = {}
            for key, value in env_overrides.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract environment variable name and get its value
                    env_var_name = value[2:-1]
                    env_var_value = os.environ.get(env_var_name)
                    if env_var_value is not None:
                        processed_env[key] = env_var_value
                    else:
                        logger.warning(f"Environment variable {env_var_name} not found, using empty string")
                        processed_env[key] = ""
                else:
                    processed_env[key] = value
            
            env.update(processed_env)
            
            return command, args, env
        
        # Determine the type of server
        install_type = installation_info.get('type', 'pip')
        
        # Default environment variables
        env = os.environ.copy()
        
        # Handle different installation types
        if install_type == 'pip':
            # For Python packages, try different launch approaches
            package = installation_info.get('package', server_name)
            
            # First, try the standard module approach
            return 'python', ['-m', server_name], env
        elif install_type == 'npm':
            # Node server
            return 'node', [server_name], env
        else:
            # Unknown server type, try a simple command
            return server_name, [], env
    
    async def disconnect(self, server_name: str) -> bool:
        """
        Disconnect from a server.
        
        Args:
            server_name: Name of the server to disconnect from
            
        Returns:
            True if disconnected successfully, False otherwise
        """
        if server_name not in self.connections:
            logger.warning(f"Not connected to server: {server_name}")
            return False
        
        try:
            # Just remove from connections - the exit stack will handle cleanup
            del self.connections[server_name]
            logger.info(f"Disconnected from server: {server_name}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from server {server_name}: {e}")
            return False
    
    async def disconnect_all(self) -> None:
        """Disconnect from all servers by closing the exit stack."""
        try:
            await self.exit_stack.aclose()
            self.connections.clear()
            # Create a new exit stack for future connections
            self.exit_stack = AsyncExitStack()
            logger.info("Disconnected from all servers")
        except Exception as e:
            logger.error(f"Error disconnecting from all servers: {e}")
    
    async def execute(self, capability: str, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given capability, finding and connecting to the right server.
        
        Args:
            capability: The capability needed (e.g., "weather", "search")
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            
        Returns:
            Dictionary with tool execution results or error information with suggestions
        """
        try:
            # Using context manager for proper cleanup
            async with self.connect_session(capability) as (server_name, client):
                # Execute the tool
                logger.info(f"Executing tool '{tool_name}' on server '{server_name}'")
                result = await client.call_tool(tool_name, parameters)
                
                logger.info(f"Tool execution completed: {tool_name}")
                return result
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error executing tool '{tool_name}': {e}")
            
            # Provide helpful error information
            suggestion = "Unknown error occurred."
            
            if "No MCP server found for capability" in error_message:
                suggestion = f"No server is available for the {capability} capability. Consider setting AUTO_INSTALL_SERVERS=true to automatically install required servers."
            elif "Failed to connect to any server" in error_message:
                suggestion = f"Unable to connect to a server for the {capability} capability. Check if the server is installed correctly."
            elif "not found in registry" in error_message:
                suggestion = "The specified server is not registered. Try updating the registry."
            elif "API key" in error_message.lower() or "unauthorized" in error_message.lower():
                suggestion = "An API key might be required. Check the server documentation for the required environment variables."
            
            return {
                "error": f"Error executing tool '{tool_name}' for capability '{capability}': {error_message}",
                "status": "error",
                "suggestion": suggestion,
                "capability": capability,
                "tool_name": tool_name
            }
            
    async def list_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List all tools available on a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of tool definitions
        """
        try:
            client = await self.connect_to_server(server_name)
            return await client.list_tools()
        except Exception as e:
            logger.error(f"Error listing tools for server {server_name}: {e}")
            raise

    async def find_server_for_capability(self, capability: str) -> Optional[Dict[str, Any]]:
        """
        Find a server that provides the requested capability
        
        This method will attempt to find an existing server for the capability.
        If none is found and auto_install is enabled, it will try to install one.
        
        Args:
            capability: The capability to search for
            
        Returns:
            Server data dictionary or None if no server is found
        """
        # Ensure registry is loaded
        if not hasattr(self.registry, 'servers') or not self.registry.servers:
            await self.registry.update()
        
        # Search for servers with the capability
        matching_servers = []
        for server in self.registry.servers:
            if capability in server.get("capabilities", []):
                matching_servers.append(server)
        
        if not matching_servers:
            logger.warning(f"No servers found for capability: {capability}")
            return None
            
        # Return the first server (could be enhanced with ranking later)
        server = matching_servers[0]
        server_name = server.get("name")
        
        # Check if server is installed
        if not self.registry.is_server_installed(server_name):
            # Check if auto-install is enabled
            auto_install = os.environ.get("AUTO_INSTALL_SERVERS", "").lower() == "true"
            
            if auto_install:
                logger.info(f"Auto-installing server for capability: {capability}")
                installed = await self.installer.install_server(server)
                
                if not installed:
                    logger.error(f"Failed to install server for capability: {capability}")
                    return None
            else:
                logger.warning(f"Server '{server_name}' is not installed and auto-install is disabled")
                return None
                
        return server
        
    async def execute_capability(
        self, 
        capability: str, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Find a server for a capability and execute a tool
        
        This is a convenience method that combines find_server_for_capability
        and execute_tool into a single operation.
        
        Args:
            capability: The capability to search for
            tool_name: The tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool execution result or error information with suggestions
        """
        # When USE_MOCK_DATA is true, use mock data instead of real servers
        if os.environ.get("USE_MOCK_DATA") == "true":
            if capability == "weather":
                location = parameters.get("location", "Unknown").lower()
                if "paris" in location:
                    return {
                        "temperature": 22,
                        "condition": "Sunny",
                        "humidity": 65,
                        "location": "Paris"
                    }
                elif "london" in location:
                    return {
                        "temperature": 18, 
                        "condition": "Cloudy",
                        "humidity": 75,
                        "location": "London"
                    }
                elif "tokyo" in location:
                    return {
                        "temperature": 28,
                        "condition": "Partly Cloudy",
                        "humidity": 60,
                        "location": "Tokyo"
                    }
                else:
                    return {
                        "temperature": 20,
                        "condition": "Unknown",
                        "humidity": 70,
                        "location": location
                    }
            elif capability == "search":
                return {
                    "results": [
                        {"title": "Search Result 1", "url": "https://example.com/1", "snippet": "This is a mock search result."},
                        {"title": "Search Result 2", "url": "https://example.com/2", "snippet": "Another mock search result."}
                    ]
                }
            elif capability == "time":
                return {
                    "time": "12:34 PM",
                    "timezone": "UTC",
                    "location": parameters.get("location", "")
                }
            else:
                # Default mock result for unknown capabilities
                return {"message": f"Mock result for capability: {capability}"}
        
        # Otherwise, use real servers
        try:
            # Ensure registry is loaded
            if not hasattr(self.registry, 'servers') or not self.registry.servers:
                await self.registry.update()
            
            # Use the registry search method to find servers with this capability
            matching_servers = self.registry.search_by_capability(capability)
            
            # If no servers found, return helpful message
            if not matching_servers:
                logger.warning(f"No servers found for capability: {capability}")
                return {
                    "error": f"No servers available for capability: {capability}",
                    "status": "error",
                    "suggestion": "No servers in the registry support this capability.",
                    "capability": capability,
                    "tool_name": tool_name
                }
                
            # Check if any servers are installed
            installed_servers = []
            for server in matching_servers:
                server_name = server.get("name")
                if self.registry.is_server_installed(server_name):
                    installed_servers.append(server)
            
            if not installed_servers:
                # Build list of available servers
                available_servers = [s.get("name") for s in matching_servers]
                
                # Check auto_install setting
                auto_install = os.environ.get("AUTO_INSTALL_SERVERS", "").lower() == "true"
                suggestion = f"Consider installing a server for the '{capability}' capability."
                if not auto_install and available_servers:
                    suggestion += " To auto-install servers, set AUTO_INSTALL_SERVERS=true in your environment variables."
                
                logger.warning(f"No installed servers for capability: {capability}")
                return {
                    "error": f"No server installed for capability: {capability}",
                    "status": "error",
                    "suggestion": suggestion,
                    "available_servers": available_servers,
                    "capability": capability
                }
                
            # If we get here, we have at least one installed server
            # Use the execute_tool method with the first server
            server = installed_servers[0]
            return await self.execute_tool(server, tool_name, parameters)
            
        except Exception as e:
            error_message = str(e)
            suggestion = "An unexpected error occurred."
            
            # Analyze common error patterns and provide helpful suggestions
            if "API key" in error_message or "Authentication" in error_message or "Unauthorized" in error_message:
                suggestion = "Check if the required API key is set in the environment variables."
                if capability == "weather":
                    suggestion += " For weather capability, set the ACCUWEATHER_API_KEY environment variable."
            elif "Connection" in error_message or "Timeout" in error_message:
                suggestion = "Check your internet connection and try again."
            elif "No such file or directory" in error_message:
                suggestion = "A required file or tool is missing. Try reinstalling the server."
            elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
                suggestion = "A required Python module is missing. Try reinstalling the server."
            elif "'str' object has no attribute 'get'" in error_message:
                suggestion = "There was an issue finding a server for this capability. Try setting AUTO_INSTALL_SERVERS=true."
            
            # Return structured error information
            return {
                "error": f"Error executing capability '{capability}' with tool '{tool_name}': {error_message}",
                "status": "error",
                "suggestion": suggestion,
                "capability": capability,
                "tool_name": tool_name
            }
            
    async def execute_tool(
        self, 
        server_data: Union[str, Dict[str, Any]], 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool on a server
        
        This method handles connecting to the server if needed, executing the tool
        with the provided parameters, and maintaining the connection for future use.
        
        Args:
            server_data: Server information (can be a server name string or server data dictionary)
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool execution result or error information with suggestions
            
        Raises:
            Exception: If tool execution fails
        """
        # Handle the case where server_data is a string (server name)
        server_name = None
        if isinstance(server_data, str):
            server_name = server_data
        elif isinstance(server_data, dict):
            server_name = server_data.get('name')
            
        if not server_name:
            return {
                "error": "Invalid server data provided",
                "status": "error",
                "suggestion": "Check that the server name is correctly specified."
            }
            
        try:
            # Connect to the server
            client = await self.connect_to_server(server_name)
            
            # Execute the tool
            logger.debug(f"Executing tool '{tool_name}' with parameters: {parameters}")
            result = await client.call_tool(tool_name, parameters)
            
            # If result is an error, provide additional context
            if isinstance(result, dict) and result.get("error"):
                error_message = result.get("error")
                suggestion = "Unknown error occurred during tool execution."
                
                # Analyze tool-specific errors
                if "API key" in str(error_message) or "Authorization" in str(error_message):
                    suggestion = "The tool requires an API key that may not be set correctly."
                    if server_name == "mcp_weather":
                        suggestion += " Set the ACCUWEATHER_API_KEY environment variable."
                
                result.update({
                    "status": "error",
                    "suggestion": suggestion,
                    "server_name": server_name,
                    "tool_name": tool_name
                })
            
            return result
        except Exception as e:
            # Provide human-readable error information
            error_message = str(e)
            suggestion = "An error occurred when executing the tool."
            
            if "not found" in error_message.lower() and tool_name in error_message:
                suggestion = f"The tool '{tool_name}' does not exist on server '{server_name}'. Check available tools with list_server_tools()."
            elif "connection" in error_message.lower():
                suggestion = "Failed to connect to the server. Check that it's running and accessible."
            elif "timeout" in error_message.lower():
                suggestion = "The server connection timed out. The operation may have taken too long."
            
            return {
                "error": f"Error executing tool '{tool_name}' on server '{server_name}': {error_message}",
                "status": "error",
                "suggestion": suggestion,
                "server_name": server_name,
                "tool_name": tool_name
            }
            
    async def aclose(self) -> None:
        """
        Close all connections and clean up resources
        
        This method should be called when the connector is no longer needed.
        """
        await self.disconnect_all() 