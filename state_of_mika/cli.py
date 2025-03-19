#!/usr/bin/env python
"""
State of Mika CLI - Command-line interface for managing MCP servers.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from state_of_mika.installer import Installer
from state_of_mika.registry import Registry


def setup_logging(verbose: bool = False) -> None:
    """Set up logging with the appropriate level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def list_servers(args: argparse.Namespace) -> None:
    """List available servers."""
    registry = Registry()
    await registry.update()
    
    if args.all:
        servers = registry.get_all_servers()
    else:
        servers = registry.get_installed_servers()
        
    if not servers:
        print("No servers available.")
        return
        
    print(f"Found {len(servers)} server(s):")
    for server in servers:
        installed = "INSTALLED" if registry.is_server_installed(server["name"]) else "NOT INSTALLED"
        print(f"  - {server['name']} (v{server['version']}) [{installed}]")
        print(f"    Description: {server['description']}")
        print(f"    Capabilities: {', '.join(server['capabilities'])}")
        print("")


async def search_servers(args: argparse.Namespace) -> None:
    """Search for servers by query."""
    registry = Registry()
    await registry.update()
    
    servers = registry.search_by_capability(args.query)
    
    if not servers:
        print(f"No servers found matching '{args.query}'.")
        return
        
    print(f"Found {len(servers)} server(s) matching '{args.query}':")
    for server in servers:
        installed = "INSTALLED" if registry.is_server_installed(server["name"]) else "NOT INSTALLED"
        print(f"  - {server['name']} (v{server['version']}) [{installed}]")
        print(f"    Description: {server['description']}")
        print(f"    Capabilities: {', '.join(server['capabilities'])}")
        print("")


async def install_server(args: argparse.Namespace) -> None:
    """Install a server by name."""
    registry = Registry()
    await registry.update()
    
    server = registry.get_server_by_name(args.name)
    if not server:
        print(f"Server '{args.name}' not found in registry.")
        return
        
    installer = Installer(registry)
    try:
        print(f"Installing {server['name']}...")
        installed = await installer.install_server(server["name"])
        if installed:
            print(f"Successfully installed {server['name']}.")
        else:
            print(f"Failed to install {server['name']}.")
    except Exception as e:
        print(f"Error installing {server['name']}: {str(e)}")


async def uninstall_server(args: argparse.Namespace) -> None:
    """Uninstall a server by name."""
    registry = Registry()
    await registry.update()
    
    server = registry.get_server_by_name(args.name)
    if not server:
        print(f"Server '{args.name}' not found in registry.")
        return
        
    installer = Installer(registry)
    try:
        print(f"Uninstalling {server['name']}...")
        uninstalled = await installer.uninstall_server(server["name"])
        if uninstalled:
            print(f"Successfully uninstalled {server['name']}.")
        else:
            print(f"Failed to uninstall {server['name']}.")
    except Exception as e:
        print(f"Error uninstalling {server['name']}: {str(e)}")


async def update_registry(args: argparse.Namespace) -> None:
    """Update the server registry."""
    registry = Registry()
    try:
        print("Updating server registry...")
        updated = await registry.update()
        if updated:
            print("Successfully updated server registry.")
        else:
            print("Server registry is already up to date.")
    except Exception as e:
        print(f"Error updating server registry: {str(e)}")


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="State of Mika CLI - Manage MCP servers"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List available servers")
    list_parser.add_argument(
        "--all", action="store_true", help="List all servers, including non-installed"
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for servers")
    search_parser.add_argument("query", help="Search query")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install a server")
    install_parser.add_argument("name", help="Server name")

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a server")
    uninstall_parser.add_argument("name", help="Server name")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update server registry")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "list":
            asyncio.run(list_servers(args))
        elif args.command == "search":
            asyncio.run(search_servers(args))
        elif args.command == "install":
            asyncio.run(install_server(args))
        elif args.command == "uninstall":
            asyncio.run(uninstall_server(args))
        elif args.command == "update":
            asyncio.run(update_registry(args))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 