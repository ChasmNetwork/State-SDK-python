"""
Server Registry for MCP Servers

Manages discovery, installation, and tracking of MCP servers.
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger("state_of_mika.registry")

class ServerRegistry:
    """
    Registry for MCP servers
    
    Handles discovery, installation, and tracking of MCP servers.
    """
    
    def __init__(self, registry_url: Optional[str] = None, server_dir: Optional[Path] = None):
        """
        Initialize a new server registry.
        
        Args:
            registry_url: URL to the server registry (optional)
            server_dir: Directory to store server files (optional)
        """
        self.registry_url = registry_url
        
        # Set default server directory if not provided
        if server_dir is None:
            home_dir = Path.home()
            self.server_dir = home_dir / '.mika' / 'servers'
        else:
            self.server_dir = server_dir
        
        # Create server directory if it doesn't exist
        os.makedirs(self.server_dir, exist_ok=True)
        
        # Load servers from embedded registry
        self.servers = {}
        self._load_default_servers()
        
        # Load user-defined servers if available
        self._load_user_servers()
    
    def _load_default_servers(self):
        """Load servers from the embedded registry."""
        # Get the path to the servers.json file in the same directory as this script
        servers_path = Path(__file__).parent / 'servers.json'
        
        try:
            with open(servers_path, 'r') as f:
                servers = json.load(f)
                
            for server in servers:
                self.servers[server['id']] = server
                
            logger.debug(f"Loaded {len(servers)} servers from default registry")
        except Exception as e:
            logger.error(f"Error loading default servers: {e}")
    
    def _load_user_servers(self):
        """Load user-defined servers from the server directory."""
        user_servers_path = self.server_dir / 'servers.json'
        
        if not user_servers_path.exists():
            return
            
        try:
            with open(user_servers_path, 'r') as f:
                servers = json.load(f)
                
            for server in servers:
                self.servers[server['id']] = server
                
            logger.debug(f"Loaded {len(servers)} servers from user registry")
        except Exception as e:
            logger.error(f"Error loading user servers: {e}")
    
    def _save_user_servers(self):
        """Save user-defined servers to the server directory."""
        # Determine which servers are user-defined
        default_servers_path = Path(__file__).parent / 'servers.json'
        default_server_ids = set()
        
        try:
            with open(default_servers_path, 'r') as f:
                default_servers = json.load(f)
                default_server_ids = {s['id'] for s in default_servers}
        except Exception as e:
            logger.error(f"Error loading default servers: {e}")
        
        # Filter out default servers
        user_servers = [
            server for server_id, server in self.servers.items()
            if server_id not in default_server_ids
        ]
        
        # Save user servers
        user_servers_path = self.server_dir / 'servers.json'
        
        try:
            with open(user_servers_path, 'w') as f:
                json.dump(user_servers, f, indent=2)
                
            logger.debug(f"Saved {len(user_servers)} user servers")
        except Exception as e:
            logger.error(f"Error saving user servers: {e}")
    
    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a server by ID.
        
        Args:
            server_id: Server ID
            
        Returns:
            Server info or None if not found
        """
        return self.servers.get(server_id)
    
    def get_all_servers(self) -> List[Dict[str, Any]]:
        """
        Get all registered servers.
        
        Returns:
            List of server info dictionaries
        """
        return list(self.servers.values())
    
    async def add_server(self, server_info: Dict[str, Any]) -> None:
        """
        Add a server to the registry.
        
        Args:
            server_info: Server info dictionary
        """
        if 'id' not in server_info:
            raise ValueError("Server info must contain 'id'")
            
        self.servers[server_info['id']] = server_info
        self._save_user_servers()
        
        logger.info(f"Added server: {server_info.get('name', server_info['id'])}")
    
    async def remove_server(self, server_id: str) -> bool:
        """
        Remove a server from the registry.
        
        Args:
            server_id: Server ID
            
        Returns:
            True if server was removed, False if not found
        """
        if server_id not in self.servers:
            return False
            
        del self.servers[server_id]
        self._save_user_servers()
        
        logger.info(f"Removed server: {server_id}")
        return True
    
    async def install_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Install an MCP server.
        
        Args:
            server_id: Server ID or package name
            
        Returns:
            Server info or None if installation failed
        """
        # Check if server is already in registry
        server_info = self.get_server(server_id)
        
        if not server_info:
            # Try to interpret as a package name
            if server_id.startswith('@'):
                package_name = server_id
            else:
                package_name = f"@modelcontextprotocol/server-{server_id}"
                
            # Create server info
            server_info = {
                "id": server_id,
                "name": server_id,
                "description": f"MCP server: {server_id}",
                "type": "local",
                "command": "npx",
                "args": [package_name],
                "packageName": package_name,
                "installType": "npm"
            }
        
        # Check installation type
        if server_info.get('installType') == 'npm' and 'packageName' in server_info:
            # Install npm package
            package_name = server_info['packageName']
            logger.info(f"Installing npm package: {package_name}")
            
            try:
                # Make sure npm is available
                result = subprocess.run(
                    ["npm", "--version"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    logger.error("npm not found. Please install Node.js and npm.")
                    return None
                
                # Install the package
                cmd = ["npm", "install", "--no-save", package_name]
                subprocess.run(
                    cmd,
                    cwd=str(self.server_dir),
                    check=True
                )
                
                logger.info(f"Successfully installed {package_name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing npm package: {e}")
                return None
                
        elif server_info.get('installType') == 'git' and 'sourceUrl' in server_info:
            # Clone git repository
            source_url = server_info['sourceUrl']
            logger.info(f"Cloning git repository: {source_url}")
            
            try:
                # Make sure git is available
                result = subprocess.run(
                    ["git", "--version"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    logger.error("git not found. Please install git.")
                    return None
                
                # Clone the repository
                repo_dir = self.server_dir / server_id
                cmd = ["git", "clone", source_url, str(repo_dir)]
                subprocess.run(cmd, check=True)
                
                # Install dependencies if package.json exists
                if (repo_dir / "package.json").exists():
                    logger.info(f"Installing dependencies for {server_id}")
                    subprocess.run(
                        ["npm", "install"],
                        cwd=str(repo_dir),
                        check=True
                    )
                    
                logger.info(f"Successfully cloned {source_url}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error cloning git repository: {e}")
                return None
        else:
            logger.warning(f"Unsupported installation type for server {server_id}")
            
        # Add server to registry if not already there
        if server_id not in self.servers:
            await self.add_server(server_info)
            
        return server_info
    
    async def refresh_registry(self) -> int:
        """
        Refresh the registry from the registry URL.
        
        Returns:
            Number of servers refreshed
        """
        if not self.registry_url:
            logger.warning("No registry URL configured")
            return 0
            
        logger.info(f"Refreshing registry from {self.registry_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.registry_url) as response:
                    response.raise_for_status()
                    registry_data = await response.json()
                    
            # Update servers
            for server in registry_data:
                if 'id' in server:
                    self.servers[server['id']] = server
                    
            # Save updated registry
            self._save_user_servers()
            
            logger.info(f"Refreshed {len(registry_data)} servers")
            return len(registry_data)
        except Exception as e:
            logger.error(f"Error refreshing registry: {e}")
            return 0