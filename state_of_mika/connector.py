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
                installer: Optional[Installer] = None,
                auto_install: Optional[bool] = None):
        """
        Initialize the Connector.
        
        Args:
            registry: Registry for MCP servers (created if None)
            installer: Installer for MCP servers (created if None)
            auto_install: Whether to automatically install servers when needed (if None, will use AUTO_INSTALL_SERVERS env var)
        """
        self.registry = registry or Registry()
        self.installer = installer or Installer(self.registry)
        
        # Set auto_install attribute if provided
        if auto_install is not None:
            self.auto_install = auto_install
        
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
            
            # Check if server is installed
            if not self.registry.is_server_installed(server_name):
                # Check if auto-install is enabled - support both environment variable and class attribute
                auto_install = (
                    os.environ.get("AUTO_INSTALL_SERVERS", "").lower() == "true" or 
                    getattr(self, "auto_install", False)
                )
                
                logger.debug(f"Auto-install for servers is: {auto_install}")
                
                if auto_install:
                    logger.info(f"Auto-installing server for capability: {capability}")
                    installed = await self.installer.install_server(server_data)
                    
                    if not installed:
                        logger.error(f"Failed to install server {server_name}")
                        continue
                else:
                    logger.warning(f"Server '{server_name}' is not installed and auto-install is disabled")
                    continue
            
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
        Connect to an MCP server.
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            ClientSession for the connected server
            
        Raises:
            ValueError: If the server is not found in the registry
            RuntimeError: If the server cannot be launched
        """
        if server_name in self.connections:
            logger.info(f"Already connected to server: {server_name}")
            return self.connections[server_name]
        
        # Get server data from registry
        server_data = self.registry.get_server_by_name(server_name)
        if not server_data:
            raise ValueError(f"Server '{server_name}' not found in registry")
        
        # Check if server is installed
        if not self.registry.is_server_installed(server_name):
            # Check if auto-install is enabled
            auto_install = (
                os.environ.get("AUTO_INSTALL_SERVERS", "").lower() == "true" or 
                getattr(self, "auto_install", False)
            )
            
            if not auto_install:
                raise ValueError(f"Server '{server_name}' is not installed and auto-install is disabled")
            
            # Install the server
            logger.info(f"Auto-installing server: {server_name}")
            installed = await self.installer.install_server(server_data)
            
            if not installed:
                raise RuntimeError(f"Failed to install server: {server_name}")
        
        try:
            # Get the command, args, and environment to launch the server
            command, args, env = self._get_server_launch_info(server_name, server_data)
            logger.info(f"Launching server: {server_name} with command: {command} {' '.join(args)}")
            
            # Get installation information to determine installation type
            installation_info = server_data.get('installation', {})
            install_info = server_data.get('install', {})
            install_type = installation_info.get('type') or install_info.get('type', 'pip')
            
            # Try to start the server
            try:
                # Create server parameters
                params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )
                
                # Connect to the server
                read_stream, write_stream = await self.exit_stack.enter_async_context(
                    stdio_client(params)
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
                        f"except ModuleNotFoundError as e: "
                        f"    missing_module = str(e).split(\"'\")"
                        f"    if len(missing_module) >= 2: "
                        f"        missing_dep = missing_module[1] "
                        f"        print(f'Missing dependency: {{missing_dep}}. Attempting auto-installation...') "
                        f"        import subprocess "
                        f"        try: "
                        f"            subprocess.check_call([sys.executable, '-m', 'pip', 'install', missing_dep]) "
                        f"            print(f'Successfully installed {{missing_dep}}') "
                        f"            # Try again with the dependency installed "
                        f"            import importlib "
                        f"            importlib.invalidate_caches() "
                        f"            import {server_name} "
                        f"            if hasattr({server_name}, 'run_server'): "
                        f"                {server_name}.run_server() "
                        f"            elif hasattr({server_name}, 'main'): "
                        f"                {server_name}.main() "
                        f"            elif hasattr({server_name}, 'start'): "
                        f"                {server_name}.start() "
                        f"            else: "
                        f"                sys.exit('Cannot find entry point for {server_name}') "
                        f"        except Exception as dep_e: "
                        f"            sys.exit(f'Failed to install missing dependency {{missing_dep}}: {{dep_e}}') "
                        f"    else: "
                        f"        sys.exit(f'Error starting {server_name}: {{e}}'); "
                        f"except Exception as e: "
                        f"    sys.exit(f'Error starting {server_name}: {{e}}'); "
                    )
                    
                    fallback_params = StdioServerParameters(
                        command='python',
                        args=['-c', script],
                        env=env
                    )
                    
                    try:
                        logger.info(f"Trying fallback launch method with auto dependency installation")
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
                        
                        logger.info(f"Connected to server using fallback method with auto dependency installation: {server_name}")
                        return session
                    except Exception as fallback_error:
                        logger.error(f"Fallback launch also failed: {fallback_error}")
                        
                        # Try one more approach - install the main package with pip --verbose to capture dependencies
                        try:
                            logger.info(f"Attempting to reinstall {server_name} with pip --verbose to resolve dependencies")
                            
                            # Get package name from install info
                            package = (installation_info.get('package') or 
                                       install_info.get('package') or 
                                       server_name)
                            
                            # Run pip install with --verbose to see what's happening
                            pip_process = await asyncio.create_subprocess_exec(
                                sys.executable, "-m", "pip", "install", "--verbose", "--force-reinstall", package,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await pip_process.communicate()
                            
                            # Log the output for debugging
                            logger.debug(f"Pip install output: {stdout.decode()}")
                            logger.debug(f"Pip install errors: {stderr.decode()}")
                            
                            # Now try launching the server again
                            logger.info(f"Attempting to launch {server_name} after reinstalling")
                            
                            # Create server parameters
                            params = StdioServerParameters(
                                command=command,
                                args=args,
                                env=env
                            )
                            
                            # Connect to the server
                            read_stream, write_stream = await self.exit_stack.enter_async_context(
                                stdio_client(params)
                            )
                            
                            session = await self.exit_stack.enter_async_context(
                                ClientSession(read_stream, write_stream)
                            )
                            
                            # Initialize the session
                            await session.initialize()
                            
                            # Store the connection
                            self.connections[server_name] = session
                            
                            logger.info(f"Connected to server: {server_name} after reinstalling package")
                            return session
                        except Exception as reinstall_error:
                            logger.error(f"Reinstallation attempt failed: {reinstall_error}")
                            raise RuntimeError(f"Could not launch server {server_name} using any method: {reinstall_error}")
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
            logger.info("📋 Loading registry data...")
            await self.registry.update()
        
        # Search for servers with the capability
        logger.info(f"🔍 Searching for servers with capability: '{capability}'")
        matching_servers = []
        for server_name, server in self.registry.servers.items():
            capabilities = server.get("capabilities", [])
            if capability in capabilities:
                logger.info(f"✓ Found server '{server_name}' with capability '{capability}'")
                matching_servers.append(server)
        
        if not matching_servers:
            logger.warning(f"❌ No servers found for capability: '{capability}'")
            return None
            
        # Return the first server (could be enhanced with ranking later)
        server = matching_servers[0]
        server_name = server.get("name")
        logger.info(f"✓ Selected server '{server_name}' for capability '{capability}'")
        
        # Check if server is installed
        if not self.registry.is_server_installed(server_name):
            # Check if auto-install is enabled - support both environment variable and class attribute
            auto_install = (
                os.environ.get("AUTO_INSTALL_SERVERS", "").lower() == "true" or 
                getattr(self, "auto_install", False)
            )
            
            logger.info(f"🔄 Auto-install for servers is: {'Enabled ✅' if auto_install else 'Disabled ❌'}")
            
            if auto_install:
                logger.info(f"🔧 Auto-installing server '{server_name}' for capability: '{capability}'")
                installed = await self.installer.install_server(server)
                
                if not installed:
                    logger.error(f"❌ Failed to install server '{server_name}' for capability: '{capability}'")
                    return None
                else:
                    logger.info(f"✅ Successfully installed server '{server_name}' for capability: '{capability}'")
            else:
                logger.warning(f"❌ Server '{server_name}' is not installed and auto-install is disabled")
                return None
        else:
            logger.info(f"✅ Server '{server_name}' is already installed")
                
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
                
                # Check auto_install setting - use both env var and class attribute
                auto_install = (
                    os.environ.get("AUTO_INSTALL_SERVERS", "").lower() == "true" or 
                    getattr(self, "auto_install", False)
                )
                
                logger.debug(f"Auto-install for servers is: {auto_install}")
                
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
                # Check for specific API key issues based on the capability
                if capability == "weather":
                    key_name = "ACCUWEATHER_API_KEY"
                    if not os.environ.get(key_name):
                        error_message = f"Missing AccuWeather API key. The {key_name} environment variable is not set."
                        suggestion = f"Set the {key_name} environment variable with your AccuWeather API key. You can get one at https://developer.accuweather.com/"
                    else:
                        suggestion = f"Check if your {key_name} is valid and has not expired. You may need to regenerate it at https://developer.accuweather.com/"
                else:
                    # Generic API key error
                    suggestion = "Check if the required API key is set in the environment variables."
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
        
        Args:
            server_data: Either a server name (string) or server data dictionary
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool execution result
        """
        # Get server name
        if isinstance(server_data, str):
            server_name = server_data
            if server_name not in self.registry.servers:
                logger.error(f"No such server: {server_name}")
                return {
                    "error": f"Server {server_name} not found in registry",
                    "status": "error",
                    "suggestion": "Check server name or update registry"
                }
            server_data = self.registry.servers[server_name]
        else:
            server_name = server_data.get("name")
            if not server_name:
                logger.error("Server data has no name field")
                return {
                    "error": "Server data has no name field",
                    "status": "error"
                }
        
        try:
            # Connect to the server (or get existing connection)
            try:
                session = await self.connect_to_server(server_name)
            except Exception as e:
                logger.error(f"Failed to connect to server {server_name}: {e}")
                
                # Check for specific errors related to missing dependencies
                error_str = str(e)
                if "No module named" in error_str or "ModuleNotFoundError" in error_str:
                    # Extract the missing module name if possible
                    missing_module = None
                    if "No module named '" in error_str:
                        parts = error_str.split("No module named '")
                        if len(parts) > 1:
                            missing_module = parts[1].split("'")[0]
                    
                    if missing_module:
                        return {
                            "error": f"Missing dependency: {missing_module}",
                            "status": "error",
                            "suggestion": f"Install the missing dependency with: pip install {missing_module}",
                            "missing_dependency": missing_module,
                            "server_name": server_name
                        }
                    else:
                        return {
                            "error": f"Missing dependency for {server_name}",
                            "status": "error", 
                            "suggestion": "The server requires dependencies that are not installed",
                            "server_name": server_name
                        }
                
                return {
                    "error": f"Failed to connect to server {server_name}: {e}",
                    "status": "error",
                    "suggestion": "Check if the server is installed and running"
                }
            
            # Check if tool is available
            try:
                tools = await session.list_tools()
                tool_names = [tool.get("name") for tool in tools]
                
                if tool_name not in tool_names:
                    logger.warning(f"Tool {tool_name} not found on server {server_name}")
                    logger.info(f"Available tools: {tool_names}")
                    
                    # Look for similar tool names as suggestions
                    similar_tools = []
                    for available_tool in tool_names:
                        if tool_name.lower() in available_tool.lower() or available_tool.lower() in tool_name.lower():
                            similar_tools.append(available_tool)
                    
                    suggestion = f"Tool {tool_name} not found on server {server_name}."
                    if similar_tools:
                        suggestion += f" Did you mean one of these: {', '.join(similar_tools)}?"
                    else:
                        suggestion += f" Available tools: {', '.join(tool_names)}"
                    
                    return {
                        "error": f"Tool {tool_name} not found on server {server_name}",
                        "status": "error",
                        "suggestion": suggestion,
                        "available_tools": tool_names
                    }
            except Exception as e:
                logger.error(f"Error listing tools on server {server_name}: {e}")
                return {
                    "error": f"Error listing tools on server {server_name}: {e}",
                    "status": "error"
                }
            
            # Execute the tool
            try:
                logger.info(f"Executing tool {tool_name} on server {server_name} with parameters: {parameters}")
                result = await session.call_tool(tool_name, parameters)
                logger.info(f"Tool {tool_name} executed successfully on server {server_name}")
                
                # Check if result contains an error
                if isinstance(result, dict) and "error" in result:
                    logger.warning(f"Tool {tool_name} returned an error: {result['error']}")
                    
                    # Check for API key errors to provide better guidance
                    error_message = str(result.get("error", ""))
                    suggestion = result.get("suggestion", "")
                    
                    if ("API key" in error_message or "Authorization" in error_message or 
                        "Unauthorized" in error_message or "authentication" in error_message.lower()):
                        
                        # Check for specific servers to provide targeted suggestions
                        if server_name == "mcp_weather":
                            env_var = "ACCUWEATHER_API_KEY"
                            if not os.environ.get(env_var):
                                suggestion = f"Set the {env_var} environment variable with your AccuWeather API key. You can get one at https://developer.accuweather.com/"
                            else:
                                suggestion = f"Check if your {env_var} is valid and has not expired. You may need to regenerate it at https://developer.accuweather.com/"
                        elif server_name == "mcp_wolfram_alpha":
                            env_var = "WOLFRAM_API_KEY"
                            if not os.environ.get(env_var):
                                suggestion = f"Set the {env_var} environment variable with your Wolfram Alpha API key. You can get one at https://products.wolframalpha.com/api/"
                            else:
                                suggestion = f"Check if your {env_var} is valid and has not expired. You may need to regenerate it at https://products.wolframalpha.com/api/"
                        else:
                            # Generic API key suggestion
                            suggestion = "This tool requires an API key. Check the server documentation for the required environment variables."
                        
                        result["status"] = "error"
                        result["suggestion"] = suggestion
                        result["server_name"] = server_name
                        result["tool_name"] = tool_name
                    
                return result
            except Exception as e:
                logger.error(f"Error executing tool {tool_name} on server {server_name}: {e}")
                
                # Check for dependency errors
                error_str = str(e)
                if "No module named" in error_str or "ModuleNotFoundError" in error_str:
                    # Extract the missing module name if possible
                    missing_module = None
                    if "No module named '" in error_str:
                        parts = error_str.split("No module named '")
                        if len(parts) > 1:
                            missing_module = parts[1].split("'")[0]
                    
                    if missing_module:
                        return {
                            "error": f"Missing dependency: {missing_module}",
                            "status": "error",
                            "suggestion": f"Install the missing dependency with: pip install {missing_module}",
                            "missing_dependency": missing_module,
                            "server_name": server_name,
                            "tool_name": tool_name
                        }
                
                return {
                    "error": f"Error executing tool {tool_name} on server {server_name}: {e}",
                    "status": "error",
                    "suggestion": "Check tool parameters and server status"
                }
        except Exception as e:
            logger.error(f"Unexpected error executing tool {tool_name}: {e}")
            return {
                "error": f"Unexpected error: {e}",
                "status": "error"
            }
            
    async def aclose(self) -> None:
        """
        Close all connections and clean up resources
        
        This method should be called when the connector is no longer needed.
        """
        await self.disconnect_all() 