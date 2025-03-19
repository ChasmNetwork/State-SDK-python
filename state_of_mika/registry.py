"""
Registry module for managing MCP servers.

This module provides functionality to:
1. Access the MCP server registry
2. Search for servers based on capabilities
3. Get server information
"""

import json
import logging
import os
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class Registry:
    """
    Registry for MCP servers.
    
    Provides access to the central registry of MCP servers and 
    allows searching for servers based on capabilities.
    """
    
    def __init__(self, 
                registry_url: Optional[str] = None,
                registry_file: Optional[Path] = None,
                cache_dir: Optional[Path] = None):
        """
        Initialize the Registry.
        
        Args:
            registry_url: URL for the remote registry (defaults to GitHub registry)
            registry_file: Path to local registry file (defaults to ~/.som/registry.json)
            cache_dir: Directory for caching registry (defaults to ~/.som)
        """
        self.home_dir = Path.home() / '.som'
        self.cache_dir = cache_dir or self.home_dir
        
        # Use the local registry.json file in our package directory if no custom path is provided
        if registry_file is None:
            import importlib.resources
            package_dir = Path(__file__).parent
            self.registry_file = package_dir / 'registry' / 'servers.json'
        else:
            self.registry_file = registry_file
            
        self.registry_url = registry_url or "https://raw.githubusercontent.com/stateofmika/registry/main/servers.json"
        
        # Create necessary directories
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Dictionary to store server data
        self.servers: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load the registry from the local file or create a new one."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    servers_list = data.get('servers', [])
                    # Convert from list to dict with server name as key
                    self.servers = {server['name']: server for server in servers_list}
                logger.info(f"Loaded {len(self.servers)} servers from registry")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading registry: {e}")
                self.servers = {}
        else:
            logger.info("No local registry found")
            self.servers = {}
    
    def _save_registry(self) -> None:
        """Save the registry to the local file."""
        try:
            # Convert dict back to list for saving
            servers_list = list(self.servers.values())
            with open(self.registry_file, 'w') as f:
                json.dump({'servers': servers_list}, f, indent=2)
            logger.info(f"Saved {len(self.servers)} servers to registry")
        except IOError as e:
            logger.error(f"Error saving registry: {e}")
    
    async def update(self, force: bool = False) -> bool:
        """
        Update the registry from the remote source.
        
        Args:
            force: Force update even if the registry was recently updated
            
        Returns:
            True if the registry was updated, False otherwise
        """
        # If we already have servers and we're not forcing an update,
        # consider the registry to be up-to-date
        if self.servers and not force:
            return False
            
        # First try to load from local file
        self._load_registry()
        
        # If we have servers now, consider it updated
        if self.servers:
            return True
            
        # Otherwise, try to fetch from remote
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.registry_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        servers_list = data.get('servers', [])
                        # Convert from list to dict with server name as key
                        self.servers = {server['name']: server for server in servers_list}
                        self._save_registry()
                        logger.info(f"Updated registry with {len(self.servers)} servers")
                        return True
                    else:
                        logger.warning(f"Failed to update registry: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error updating registry: {e}")
            return False
    
    def get_all_servers(self) -> List[Dict[str, Any]]:
        """
        Get all servers in the registry.
        
        Returns:
            List of all servers
        """
        return list(self.servers.values())
    
    def get_installed_servers(self) -> List[Dict[str, Any]]:
        """
        Get all installed servers.
        
        Returns:
            List of installed servers
        """
        # For now, we'll just return all servers
        # In a real implementation, we'd check which ones are installed
        return self.get_all_servers()
        
    def is_server_installed(self, server_name: str) -> bool:
        """
        Check if a server is installed
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            True if the server is installed, False otherwise
        """
        if server_name not in self.servers:
            logger.warning(f"Server {server_name} not found in registry")
            return False
            
        server = self.servers[server_name]
        
        # Check if the server has installation information
        install_info = server.get("install") or server.get("installation", {})
        if not install_info:
            logger.warning(f"No installation information for server {server_name}")
            return False
            
        install_type = install_info.get("type")
        
        # For pip packages, check if the package can be imported
        if install_type == "pip":
            package_name = install_info.get("package", "")
            
            # Extract package name from GitHub URL if necessary
            if "github.com" in package_name:
                # Try to extract the repo name from the URL
                try:
                    repo_parts = package_name.split("/")
                    # Extract just the repository name without .git extension
                    package_name = repo_parts[-1].replace(".git", "").replace("mcp-", "").replace("-", "_")
                except:
                    pass
                    
            # Special case for mcp_weather
            if server_name == "mcp_weather":
                package_name = "mcp_weather"
                
            if not package_name:
                return False
                
            # Check if the package can be imported
            try:
                importlib = __import__("importlib")
                importlib.util.find_spec(package_name)
                logger.debug(f"Package {package_name} is installed")
                return True
            except (ImportError, ModuleNotFoundError, AttributeError):
                # Try to import directly
                try:
                    __import__(package_name)
                    logger.debug(f"Package {package_name} is installed (direct import)")
                    return True
                except:
                    logger.debug(f"Package {package_name} is not installed")
                    return False
                    
        # For npm packages, check if the package is installed with npm list
        elif install_type == "npm":
            return False  # Not supported yet
            
        return False
    
    def search_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Search for servers supporting a specific capability
        
        Args:
            capability: The capability to search for
            
        Returns:
            List of server dictionaries that support the capability
        """
        if not self.servers:
            logger.warning("Registry is empty, cannot search for capability")
            return []
            
        matching_servers = []
        for server_name, server_data in self.servers.items():
            # Check if the capability is in the server's capabilities list
            if capability in server_data.get("capabilities", []):
                # Include the name in the server data if not already there
                server_info = server_data.copy()
                if "name" not in server_info:
                    server_info["name"] = server_name
                matching_servers.append(server_info)
                
        return matching_servers
    
    def find_servers_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Alias for search_by_capability for backward compatibility.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of matching servers
        """
        logger.debug(f"Finding servers for capability: {capability}")
        return self.search_by_capability(capability)
    
    def get_server_by_name(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get server data by name.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server data or None if not found
        """
        return self.servers.get(server_name) 