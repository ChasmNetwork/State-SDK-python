#!/usr/bin/env python3
"""
Example of manually installing and using an MCP server without the State of Mika SDK.

This demonstrates the manual steps needed for:
1. Installing the server and its dependencies
2. Connecting to the server
3. Executing tools
4. Handling errors
"""

import os
import sys
import asyncio
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("manual_mcp_example")

async def install_server(server_name, package_name=None):
    """Manually install an MCP server using pip."""
    logger.info(f"Installing MCP server: {server_name}")
    
    # Use the server name as package name if not specified
    package_name = package_name or server_name
    
    try:
        # Execute pip install
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", package_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"Successfully installed {server_name}")
            return True
        else:
            error_msg = stderr.decode()
            logger.error(f"Error installing {server_name}: {error_msg}")
            return False
    except Exception as e:
        logger.error(f"Exception during installation: {e}")
        return False

async def install_dependency(dependency_name):
    """Manually install a dependency for an MCP server."""
    logger.info(f"Installing dependency: {dependency_name}")
    
    try:
        # Execute pip install
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", dependency_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info(f"Successfully installed dependency {dependency_name}")
            return True
        else:
            error_msg = stderr.decode()
            logger.error(f"Error installing dependency {dependency_name}: {error_msg}")
            return False
    except Exception as e:
        logger.error(f"Exception during dependency installation: {e}")
        return False

async def connect_to_server(server_name):
    """Connect to an MCP server."""
    logger.info(f"Connecting to server: {server_name}")
    
    try:
        # First make sure we have MCP installed
        try:
            import mcp
        except ImportError:
            logger.info("MCP package not installed, installing now...")
            await install_server("mcp")
            import mcp
        
        # Import required components from MCP
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        # Create an exit stack for resource management
        from contextlib import AsyncExitStack
        exit_stack = AsyncExitStack()
        
        # Set up parameters for launching the server
        params = StdioServerParameters(
            command="python",
            args=["-m", server_name],
            env=os.environ.copy()
        )
        
        logger.info(f"Launching server: {server_name}")
        
        try:
            # Connect to the server
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(params)
            )
            
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            # Initialize the session
            await session.initialize()
            
            logger.info(f"Successfully connected to server: {server_name}")
            return session, exit_stack
        except Exception as e:
            logger.error(f"Error launching server: {e}")
            
            # Check if it's a missing module error
            error_msg = str(e)
            if "No module named" in error_msg:
                missing_module = None
                if "No module named '" in error_msg:
                    parts = error_msg.split("No module named '")
                    if len(parts) > 1:
                        missing_module = parts[1].split("'")[0]
                
                if missing_module:
                    logger.info(f"Detected missing dependency: {missing_module}")
                    logger.info(f"Attempting to install missing dependency...")
                    
                    await install_dependency(missing_module)
                    
                    # Try again after installing the dependency
                    logger.info(f"Retrying server connection after installing dependency...")
                    return await connect_to_server(server_name)
            
            # If we get here, the error wasn't fixed
            await exit_stack.aclose()
            raise e
    except Exception as e:
        logger.error(f"Failed to connect to server {server_name}: {e}")
        raise

async def execute_weather_tool(session, location="London"):
    """Execute a weather tool on the connected server."""
    logger.info(f"Executing weather tool for location: {location}")
    
    try:
        # List available tools
        tools = await session.list_tools()
        tool_names = [tool.get("name") for tool in tools]
        logger.info(f"Available tools: {tool_names}")
        
        # Look for a weather-related tool
        weather_tool = None
        for name in tool_names:
            if "weather" in name.lower():
                weather_tool = name
                break
        
        if not weather_tool:
            logger.error("No weather tool found on this server")
            return {"error": "No weather tool available"}
        
        # Execute the tool
        logger.info(f"Executing tool: {weather_tool}")
        result = await session.call_tool(weather_tool, {"location": location})
        
        # Check for API key errors
        if isinstance(result, dict) and "error" in result:
            error_msg = result["error"]
            logger.error(f"Error from tool: {error_msg}")
            
            if "API key" in error_msg or "Authorization" in error_msg:
                logger.error("API key error detected")
                logger.info("You need to set the ACCUWEATHER_API_KEY environment variable")
                logger.info("Get an API key from https://developer.accuweather.com/")
        
        return result
    except Exception as e:
        logger.error(f"Error executing tool: {e}")
        return {"error": str(e)}

async def main():
    """Main function demonstrating manual MCP server usage."""
    print("\n================================")
    print("Manual MCP Server Example (without State of Mika SDK)")
    print("================================\n")
    
    # Define the server we want to use
    server_name = "mcp_weather"
    
    # Step 1: Install the server
    print("\n--- Step 1: Installing Server ---")
    success = await install_server(server_name)
    if not success:
        print("\nFailed to install server. Exiting.")
        return
    
    try:
        # Step 2: Connect to the server
        print("\n--- Step 2: Connecting to Server ---")
        session, exit_stack = await connect_to_server(server_name)
        
        try:
            # Step 3: Execute a tool on the server
            print("\n--- Step 3: Executing Tool ---")
            result = await execute_weather_tool(session, "Paris")
            
            print("\n--- Results ---")
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Weather in Paris:")
                if isinstance(result, dict):
                    for key, value in result.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {result}")
            
        finally:
            # Step 4: Clean up
            print("\n--- Step 4: Cleaning Up ---")
            await exit_stack.aclose()
            print("Disconnected from server")
    
    except Exception as e:
        print(f"\nError: {e}")
        print("\nManual troubleshooting required:")
        print("1. Check if the server is installed correctly with 'pip list | grep mcp'")
        print("2. Check if all dependencies are installed")
        print("3. Check if API keys are set in environment variables")
        print("4. Try reinstalling the server with 'pip install --force-reinstall mcp_weather'")
    
    print("\n================================")
    print("Example completed")
    print("================================")

if __name__ == "__main__":
    asyncio.run(main()) 