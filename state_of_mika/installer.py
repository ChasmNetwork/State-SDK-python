#!/usr/bin/env python
"""
Installer module for State of Mika SDK

This module provides the Installer class for installing and managing
MCP servers.
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class Installer:
    """
    Installer for MCP servers
    
    This class provides methods for installing, uninstalling, and managing
    MCP servers based on the information in the registry.
    """
    
    def __init__(self, registry=None):
        """
        Initialize a new Installer instance
        
        Args:
            registry: Registry instance (will be imported if None)
        """
        if registry is None:
            # Import here to avoid circular imports
            from .registry import Registry
            self.registry = Registry()
        else:
            self.registry = registry
            
    async def install_server(self, server_data: Union[str, Dict[str, Any]]) -> bool:
        """
        Install an MCP server
        
        Args:
            server_data: Either a server name (string) or server data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.registry.servers:
            logger.error("Registry is empty, cannot install server")
            return False
            
        # If server_data is a string (server name), look it up in the registry
        if isinstance(server_data, str):
            server_name = server_data
            if server_name not in self.registry.servers:
                logger.error(f"Server {server_name} not found in registry")
                return False
            server_data = self.registry.servers[server_name]
        else:
            server_name = server_data.get("name")
            
        if not server_name:
            logger.error("Server data is missing 'name' field")
            return False
            
        # Skip if already installed
        if self.registry.is_server_installed(server_name):
            logger.info(f"Server {server_name} is already installed")
            return True
            
        # Get installation details - try both "install" and "installation" keys
        install_info = server_data.get("install")
        if not install_info:
            # Try alternate key
            install_info = server_data.get("installation")
            
        if not install_info:
            logger.error(f"No installation information for server {server_name}")
            return False
            
        install_type = install_info.get("type")
        if not install_type:
            logger.error(f"No installation type specified for server {server_name}")
            return False
            
        # Install based on type
        if install_type == "pip":
            return await self._install_pip(server_name, install_info)
        elif install_type == "npm":
            return await self._install_npm(server_name, install_info)
        else:
            logger.error(f"Unsupported installation type: {install_type}")
            return False
            
    async def _install_pip(self, server_name: str, install_info: Dict[str, Any]) -> bool:
        """
        Install an MCP server via pip
        
        Args:
            server_name: Name of the server
            install_info: Installation information for the server
            
        Returns:
            True if the server was installed successfully
            
        Raises:
            ValueError: If the server data is invalid or missing installation information
        """
        package = install_info.get("package")
        if not package:
            raise ValueError(f"No package specified for pip installation of {server_name}")
            
        version = install_info.get("version", "")
        repository = install_info.get("repository")
        
        if version and not repository:
            package = f"{package}=={version}"
        
        # Try uv first, then fall back to pip if uv is not installed
        logger.info(f"Installing package with uv: {package}")
        
        # For GitHub repositories, install directly from the repo
        if repository:
            # Convert GitHub SSH URLs to HTTPS URLs to avoid authentication issues
            if "github.com" in repository and not repository.startswith("https://"):
                # Transform SSH URL format to HTTPS format
                if repository.startswith("git@github.com:"):
                    repository = repository.replace("git@github.com:", "https://github.com/")
                elif repository.startswith("ssh://git@github.com/"):
                    repository = repository.replace("ssh://git@github.com/", "https://github.com/")
                    
                logger.info(f"Converted repository URL to HTTPS format: {repository}")
                
            # Use the repository URL instead of the package name
            install_target = repository
            logger.info(f"Installing from repository: {repository}")
        else:
            install_target = package
        
        try:
            # Try with uv first
            process = await asyncio.create_subprocess_exec(
                "uv", "pip", "install", install_target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully installed {install_target} with uv")
                return True
            
            # uv command failed, check if it's not installed or another error
            error_message = stderr.decode()
            if "command not found" in error_message or "No such file or directory" in error_message:
                logger.warning("uv not found, falling back to pip")
                # Fall back to pip
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "install", install_target,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error installing {install_target} with pip: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully installed {install_target} with pip")
                return True
            else:
                logger.error(f"Error installing {install_target} with uv: {error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error during package installation: {e}")
            
            # Try falling back to pip
            try:
                logger.warning(f"Falling back to pip for installing {install_target}")
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "install", install_target,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error installing {install_target} with pip: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully installed {install_target} with pip")
                return True
            except Exception as e2:
                logger.error(f"Error during fallback to pip: {e2}")
                return False
            
    async def _install_npm(self, server_name: str, install_info: Dict[str, Any]) -> bool:
        """
        Install an MCP server via npm
        
        Args:
            server_name: Name of the server
            install_info: Installation information for the server
            
        Returns:
            True if the server was installed successfully
            
        Raises:
            ValueError: If the server data is invalid or missing installation information
        """
        package = install_info.get("package")
        if not package:
            raise ValueError(f"No package specified for npm installation of {server_name}")
            
        version = install_info.get("version", "")
        repository = install_info.get("repository")
        if version and not repository:
            package = f"{package}@{version}"
        
        # Check if npm is installed
        try:
            check_process = await asyncio.create_subprocess_exec(
                "npm", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await check_process.communicate()
            
            if check_process.returncode != 0:
                logger.error("npm is not installed or not in the PATH")
                return False
        except Exception as e:
            logger.error(f"Error checking npm installation: {e}")
            return False
            
        # For npm packages, check if the package should be installed globally
        global_install = install_info.get("global", False)
        
        # If a repository URL is specified, extract the owner and repo name for direct tarball download
        if repository and "github.com" in repository:
            try:
                # Extract the owner and repo name from the URL
                github_parts = None
                if "github.com/" in repository:
                    github_parts = repository.split("github.com/")[1].split(".git")[0].split("/")
                elif "github.com:" in repository:
                    github_parts = repository.split("github.com:")[1].split(".git")[0].split("/")
                
                if github_parts and len(github_parts) >= 2:
                    owner, repo = github_parts[0], github_parts[1]
                    
                    # Use tarball URL instead of git URL
                    tarball_url = f"https://github.com/{owner}/{repo}/tarball/main"
                    logger.info(f"Installing npm package from GitHub tarball: {tarball_url}")
                    
                    install_args = ["npm", "install"]
                    if global_install:
                        install_args.append("-g")
                    
                    install_args.append(tarball_url)
                    
                    process = await asyncio.create_subprocess_exec(
                        *install_args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_message = stderr.decode()
                        logger.error(f"Error installing npm package from tarball: {error_message}")
                        
                        # Fall back to standard npm install if tarball install fails
                        logger.info(f"Falling back to standard npm install for {package}")
                    else:
                        logger.info(f"Successfully installed npm package from tarball")
                        return True
                else:
                    logger.warning(f"Could not parse GitHub repository URL: {repository}")
            except Exception as e:
                logger.error(f"Error parsing GitHub repository URL or installing from tarball: {e}")
        
        # Standard npm installation (as fallback)
        install_args = ["npm", "install"]
        if global_install:
            install_args.append("-g")
        
        if repository:
            # Convert GitHub SSH URLs to HTTPS URLs to avoid authentication issues
            if "github.com" in repository and not repository.startswith("https://"):
                # Transform SSH URL format to HTTPS format
                if repository.startswith("git@github.com:"):
                    repository = repository.replace("git@github.com:", "https://github.com/")
                elif repository.startswith("ssh://git@github.com/"):
                    repository = repository.replace("ssh://git@github.com/", "https://github.com/")
                
                # Ensure .git extension is present
                if not repository.endswith(".git"):
                    repository += ".git"
                    
                logger.info(f"Converted repository URL to HTTPS format: {repository}")
            
            install_args.append(repository)
            logger.info(f"Installing npm package from repository: {repository} {'(globally)' if global_install else ''}")
        else:
            install_args.append(package)
            logger.info(f"Installing npm package: {package} {'(globally)' if global_install else ''}")
        
        # Run npm install
        try:
            process = await asyncio.create_subprocess_exec(
                *install_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode()
                logger.error(f"Error installing npm package: {error_message}")
                return False
                
            logger.info(f"Successfully installed npm package")
            return True
        except Exception as e:
            logger.error(f"Error during npm installation: {e}")
            return False
        
    async def uninstall_server(self, server_name: str) -> bool:
        """
        Uninstall an MCP server
        
        Args:
            server_name: Name of the server to uninstall
            
        Returns:
            True if the server was uninstalled successfully
            
        Raises:
            ValueError: If the server is not found in the registry
        """
        server_data = self.registry.get_server_by_name(server_name)
        if not server_data:
            logger.warning(f"No installation information for server: {server_name}")
            return False
            
        installation_info = server_data.get("installation")
        if not installation_info:
            logger.warning(f"No installation information for server: {server_name}")
            return False
            
        install_type = installation_info.get("type")
        if not install_type:
            raise ValueError(f"No installation type specified for server: {server_name}")
            
        logger.info(f"Installing server: {server_name}")
        
        try:
            if install_type == "pip":
                # Install via uv (faster modern Python package installer)
                package = installation_info.get("package")
                if not package:
                    raise ValueError(f"No package specified for pip installation of {server_name}")
                    
                version = installation_info.get("version", "")
                repository = installation_info.get("repository")
                
                if version and not repository:
                    package = f"{package}=={version}"
                
                # Try uv first, then fall back to pip if uv is not installed
                logger.info(f"Installing package with uv: {package}")
                
                # For GitHub repositories, install directly from the repo
                if repository:
                    # Convert GitHub SSH URLs to HTTPS URLs to avoid authentication issues
                    if "github.com" in repository and not repository.startswith("https://"):
                        # Transform SSH URL format to HTTPS format
                        if repository.startswith("git@github.com:"):
                            repository = repository.replace("git@github.com:", "https://github.com/")
                        elif repository.startswith("ssh://git@github.com/"):
                            repository = repository.replace("ssh://git@github.com/", "https://github.com/")
                            
                        logger.info(f"Converted repository URL to HTTPS format: {repository}")
                        
                    # Use the repository URL instead of the package name
                    install_target = repository
                    logger.info(f"Installing from repository: {repository}")
                else:
                    install_target = package
                
                try:
                    # Try with uv first
                    process = await asyncio.create_subprocess_exec(
                        "uv", "pip", "install", install_target,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        logger.info(f"Successfully installed {install_target} with uv")
                        return True
                    
                    # uv command failed, check if it's not installed or another error
                    error_message = stderr.decode()
                    if "command not found" in error_message or "No such file or directory" in error_message:
                        logger.warning("uv not found, falling back to pip")
                        # Fall back to pip
                        process = await asyncio.create_subprocess_exec(
                            sys.executable, "-m", "pip", "install", install_target,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            logger.error(f"Error installing {install_target} with pip: {stderr.decode()}")
                            return False
                            
                        logger.info(f"Successfully installed {install_target} with pip")
                        return True
                    else:
                        logger.error(f"Error installing {install_target} with uv: {error_message}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error during package installation: {e}")
                    
                    # Try falling back to pip
                    try:
                        logger.warning(f"Falling back to pip for installing {install_target}")
                        process = await asyncio.create_subprocess_exec(
                            sys.executable, "-m", "pip", "install", install_target,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            logger.error(f"Error installing {install_target} with pip: {stderr.decode()}")
                            return False
                            
                        logger.info(f"Successfully installed {install_target} with pip")
                        return True
                    except Exception as e2:
                        logger.error(f"Error during fallback to pip: {e2}")
                        return False
                
            elif install_type == "docker":
                # Install via docker
                image = installation_info.get("image")
                if not image:
                    raise ValueError(f"No image specified for docker installation of {server_name}")
                    
                logger.info(f"Pulling docker image: {image}")
                
                # Run docker pull
                process = await asyncio.create_subprocess_exec(
                    "docker", "pull", image,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error pulling docker image {image}: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully pulled docker image {image}")
                return True
                
            elif install_type == "script":
                # Install via script
                script = installation_info.get("script")
                if not script:
                    raise ValueError(f"No script specified for script installation of {server_name}")
                    
                logger.info(f"Running installation script: {script}")
                
                # Run the script
                process = await asyncio.create_subprocess_shell(
                    script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error running script for {server_name}: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully ran script for {server_name}")
                return True
                
            elif install_type == "npm":
                # Install via npm
                package = installation_info.get("package")
                if not package:
                    raise ValueError(f"No package specified for npm installation of {server_name}")
                    
                version = installation_info.get("version", "")
                repository = installation_info.get("repository")
                if version and not repository:
                    package = f"{package}@{version}"
                
                # Check if npm is installed
                try:
                    check_process = await asyncio.create_subprocess_exec(
                        "npm", "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await check_process.communicate()
                    
                    if check_process.returncode != 0:
                        logger.error("npm is not installed or not in the PATH")
                        return False
                except Exception as e:
                    logger.error(f"Error checking npm installation: {e}")
                    return False
                    
                # For npm packages, check if the package should be installed globally
                global_install = installation_info.get("global", False)
                
                # If a repository URL is specified, extract the owner and repo name for direct tarball download
                if repository and "github.com" in repository:
                    try:
                        # Extract the owner and repo name from the URL
                        github_parts = None
                        if "github.com/" in repository:
                            github_parts = repository.split("github.com/")[1].split(".git")[0].split("/")
                        elif "github.com:" in repository:
                            github_parts = repository.split("github.com:")[1].split(".git")[0].split("/")
                        
                        if github_parts and len(github_parts) >= 2:
                            owner, repo = github_parts[0], github_parts[1]
                            
                            # Use tarball URL instead of git URL
                            tarball_url = f"https://github.com/{owner}/{repo}/tarball/main"
                            logger.info(f"Installing npm package from GitHub tarball: {tarball_url}")
                            
                            install_args = ["npm", "install"]
                            if global_install:
                                install_args.append("-g")
                            
                            install_args.append(tarball_url)
                            
                            process = await asyncio.create_subprocess_exec(
                                *install_args,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            
                            stdout, stderr = await process.communicate()
                            
                            if process.returncode != 0:
                                error_message = stderr.decode()
                                logger.error(f"Error installing npm package from tarball: {error_message}")
                                
                                # Fall back to standard npm install if tarball install fails
                                logger.info(f"Falling back to standard npm install for {package}")
                            else:
                                logger.info(f"Successfully installed npm package from tarball")
                                return True
                        else:
                            logger.warning(f"Could not parse GitHub repository URL: {repository}")
                    except Exception as e:
                        logger.error(f"Error parsing GitHub repository URL or installing from tarball: {e}")
                
                # Standard npm installation (as fallback)
                install_args = ["npm", "install"]
                if global_install:
                    install_args.append("-g")
                
                if repository:
                    # Convert GitHub SSH URLs to HTTPS URLs to avoid authentication issues
                    if "github.com" in repository and not repository.startswith("https://"):
                        # Transform SSH URL format to HTTPS format
                        if repository.startswith("git@github.com:"):
                            repository = repository.replace("git@github.com:", "https://github.com/")
                        elif repository.startswith("ssh://git@github.com/"):
                            repository = repository.replace("ssh://git@github.com/", "https://github.com/")
                        
                        # Ensure .git extension is present
                        if not repository.endswith(".git"):
                            repository += ".git"
                            
                        logger.info(f"Converted repository URL to HTTPS format: {repository}")
                    
                    install_args.append(repository)
                    logger.info(f"Installing npm package from repository: {repository} {'(globally)' if global_install else ''}")
                else:
                    install_args.append(package)
                    logger.info(f"Installing npm package: {package} {'(globally)' if global_install else ''}")
                
                # Run npm install
                try:
                    process = await asyncio.create_subprocess_exec(
                        *install_args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_message = stderr.decode()
                        logger.error(f"Error installing npm package: {error_message}")
                        return False
                        
                    logger.info(f"Successfully installed npm package")
                    return True
                except Exception as e:
                    logger.error(f"Error during npm installation: {e}")
                    return False
                
            else:
                logger.error(f"Unsupported installation type: {install_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing server {server_name}: {e}")
            return False
            
    async def uninstall_server(self, server_name: str) -> bool:
        """
        Uninstall an MCP server
        
        Args:
            server_name: Name of the server to uninstall
            
        Returns:
            True if the server was uninstalled successfully
            
        Raises:
            ValueError: If the server is not found in the registry
        """
        server_data = self.registry.get_server_by_name(server_name)
        if not server_data:
            raise ValueError(f"Server not found in registry: {server_name}")
            
        installation_info = server_data.get("installation")
        if not installation_info:
            logger.warning(f"No installation information for server: {server_name}")
            return False
            
        install_type = installation_info.get("type")
        if not install_type:
            logger.warning(f"No installation type specified for server: {server_name}")
            return False
            
        logger.info(f"Uninstalling server: {server_name}")
        
        try:
            if install_type == "pip":
                # Uninstall via pip
                package = installation_info.get("package")
                if not package:
                    logger.warning(f"No package specified for pip uninstallation of {server_name}")
                    return False
                    
                logger.info(f"Uninstalling package: {package}")
                
                # Run pip uninstall
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "uninstall", "-y", package,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error uninstalling {package}: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully uninstalled {package}")
                return True
                
            elif install_type == "docker":
                # Uninstall via docker
                image = installation_info.get("image")
                if not image:
                    logger.warning(f"No image specified for docker uninstallation of {server_name}")
                    return False
                    
                logger.info(f"Removing docker image: {image}")
                
                # Run docker rmi
                process = await asyncio.create_subprocess_exec(
                    "docker", "rmi", image,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error removing docker image {image}: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully removed docker image {image}")
                return True
                
            elif install_type == "script":
                # Uninstall via script
                uninstall_script = installation_info.get("uninstall_script")
                if not uninstall_script:
                    logger.warning(f"No uninstall script specified for {server_name}")
                    return False
                    
                logger.info(f"Running uninstallation script: {uninstall_script}")
                
                # Run the script
                process = await asyncio.create_subprocess_shell(
                    uninstall_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Error running uninstall script for {server_name}: {stderr.decode()}")
                    return False
                    
                logger.info(f"Successfully ran uninstall script for {server_name}")
                return True
                
            elif install_type == "npm":
                # Uninstall via npm
                package = installation_info.get("package")
                if not package:
                    logger.warning(f"No package specified for npm uninstallation of {server_name}")
                    return False
                    
                # For npm packages, check if the package was installed globally
                global_install = installation_info.get("global", False)
                uninstall_args = ["npm", "uninstall"]
                
                if global_install:
                    uninstall_args.append("-g")
                    
                uninstall_args.append(package)
                logger.info(f"Uninstalling npm package: {package} {'(globally)' if global_install else ''}")
                
                # Run npm uninstall
                try:
                    process = await asyncio.create_subprocess_exec(
                        *uninstall_args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        logger.error(f"Error uninstalling npm package {package}: {stderr.decode()}")
                        return False
                        
                    logger.info(f"Successfully uninstalled npm package {package}")
                    return True
                except Exception as e:
                    logger.error(f"Error during npm uninstallation: {e}")
                    return False
                
            else:
                logger.error(f"Unsupported installation type: {install_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error uninstalling server {server_name}: {e}")
            return False
            
    async def update_server(self, server_name: str) -> bool:
        """
        Update an MCP server to the latest version
        
        Args:
            server_name: Name of the server to update
            
        Returns:
            True if the server was updated successfully
            
        Raises:
            ValueError: If the server is not found in the registry
        """
        # First uninstall the server
        uninstalled = await self.uninstall_server(server_name)
        if not uninstalled:
            logger.error(f"Failed to uninstall server {server_name} for update")
            return False
            
        # Then install the server again (with the latest version)
        server_data = self.registry.get_server_by_name(server_name)
        if not server_data:
            logger.error(f"Server {server_name} not found in registry after uninstall")
            return False
            
        return await self.install_server(server_data)
        
    async def list_installed_servers(self) -> List[str]:
        """
        List all installed MCP servers
        
        Returns:
            List of installed server names
        """
        installed_servers = []
        
        # Ensure registry is loaded
        if not hasattr(self.registry, 'servers') or not self.registry.servers:
            await self.registry.load()
            
        for server_name in self.registry.servers:
            if self.registry.is_server_installed(server_name):
                installed_servers.append(server_name)
                
        return installed_servers 