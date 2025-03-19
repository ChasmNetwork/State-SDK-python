import os
import sys
import json
import asyncio
import subprocess
import logging
from typing import Dict, Any, List, Optional, Union
import shlex
import platform

logger = logging.getLogger("state_of_mika.launcher")

class Launcher:
    """
    Launcher for MCP servers
    """

    def __init__(self, registry):
        """
        Initialize the Launcher with the specified registry
        """
        self.registry = registry
        self.server_processes = {}

    def _expand_env_vars(self, value: str) -> str:
        """
        Expand environment variables in string values
        
        Supports both ${VAR} and $VAR formats
        
        Args:
            value: String value that might contain environment variables
            
        Returns:
            String with environment variables expanded
        """
        if not isinstance(value, str):
            return value
            
        # Handle ${VAR} format
        if '${' in value and '}' in value:
            import re
            pattern = r'\${([^}]+)}'
            
            def replace_var(match):
                var_name = match.group(1)
                return os.environ.get(var_name, '')
                
            return re.sub(pattern, replace_var, value)
            
        # Handle $VAR format
        elif '$' in value:
            for env_var, env_value in os.environ.items():
                value = value.replace(f"${env_var}", env_value)
                
        return value
        
    def _expand_env_in_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively expand environment variables in a dictionary
        
        Args:
            config: Dictionary that might contain environment variables
            
        Returns:
            Dictionary with environment variables expanded
        """
        result = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                result[key] = self._expand_env_in_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._expand_env_in_dict(item) if isinstance(item, dict) else
                    self._expand_env_vars(item) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, str):
                result[key] = self._expand_env_vars(value)
            else:
                result[key] = value
                
        return result

    async def launch_server(self, server_name: str) -> bool:
        """
        Launch an MCP server
        
        Args:
            server_name: Name of the server to launch
            
        Returns:
            True if successful, False otherwise
        """
        if not self.registry.servers:
            logger.error("Registry is empty, cannot launch server")
            return False
            
        if server_name not in self.registry.servers:
            logger.error(f"Server {server_name} not found in registry")
            return False
            
        server = self.registry.servers[server_name]
        
        # Check if the server is already running
        if server_name in self.server_processes and self.server_processes[server_name].poll() is None:
            logger.info(f"Server {server_name} is already running")
            return True
            
        # Try to launch using the launch configuration
        if "launch" in server:
            launch_config = server["launch"]
            
            # Expand environment variables in the launch configuration
            launch_config = self._expand_env_in_dict(launch_config)
            
            command = launch_config.get("command")
            args = launch_config.get("args", [])
            cwd = launch_config.get("cwd")
            env_vars = launch_config.get("env", {})
            
            if not command:
                logger.error(f"No command specified for server {server_name}")
                return False
                
            # Prepare the environment
            env = os.environ.copy()
            for key, value in env_vars.items():
                env[key] = str(value)
                
            # Prepare the full command
            full_command = [command] + args
            
            try:
                # Create a single string for logging
                cmd_str = " ".join([shlex.quote(str(part)) for part in full_command])
                logger.info(f"Launching server {server_name} with command: {cmd_str}")
                
                # Start the process
                process = subprocess.Popen(
                    full_command,
                    env=env,
                    cwd=cwd
                )
                
                self.server_processes[server_name] = process
                
                # Quick check if process started successfully
                if process.poll() is not None:
                    logger.error(f"Server {server_name} failed to start")
                    return False
                    
                return True
                
            except Exception as e:
                logger.error(f"Error launching server {server_name}: {str(e)}")
                return False
                
        else:
            logger.error(f"No launch configuration for server {server_name}")
            return False 