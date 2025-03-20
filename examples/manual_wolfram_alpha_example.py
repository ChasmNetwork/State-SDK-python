#!/usr/bin/env python3
"""
Example of manually installing and using the Wolfram Alpha MCP server without the State of Mika SDK.

This demonstrates:
1. The complexity of installing servers with dependencies
2. The manual error handling required for dependency issues
3. The need to set up API keys manually
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
logger = logging.getLogger("manual_wolfram_example")

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

def check_dependency_installed(dependency_name):
    """Check if a dependency is installed."""
    try:
        __import__(dependency_name)
        return True
    except ImportError:
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

async def ensure_server_dependencies(server_name):
    """Ensure all dependencies for a server are installed."""
    logger.info(f"Checking dependencies for {server_name}")
    
    # Known dependencies for servers
    known_dependencies = {
        "mcp_wolfram_alpha": ["wolframalpha"],
        # Add other servers and their dependencies as needed
    }
    
    # Install known dependencies if any
    if server_name in known_dependencies:
        for dependency in known_dependencies[server_name]:
            if not check_dependency_installed(dependency):
                logger.info(f"Missing dependency {dependency} for {server_name}, installing...")
                await install_dependency(dependency)
            else:
                logger.info(f"Dependency {dependency} is already installed")
    
    return True

async def connect_to_server(server_name):
    """Connect to an MCP server."""
    logger.info(f"Connecting to server: {server_name}")
    
    # First ensure all known dependencies are installed
    await ensure_server_dependencies(server_name)
    
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

async def execute_wolfram_tool(session, query="solve x^2 + 2x - 3 = 0"):
    """Execute a Wolfram Alpha tool on the connected server."""
    logger.info(f"Executing Wolfram Alpha query: {query}")
    
    try:
        # List available tools
        tools = await session.list_tools()
        tool_names = [tool.get("name") for tool in tools]
        logger.info(f"Available tools: {tool_names}")
        
        # Look for a query tool
        query_tool = None
        for name in tool_names:
            if "query" in name.lower():
                query_tool = name
                break
        
        if not query_tool:
            logger.error("No query tool found on this server")
            return {"error": "No query tool available"}
        
        # Execute the tool
        logger.info(f"Executing tool: {query_tool}")
        result = await session.call_tool(query_tool, {"query": query})
        
        # Check for API key errors
        if isinstance(result, dict) and "error" in result:
            error_msg = result["error"]
            logger.error(f"Error from tool: {error_msg}")
            
            if "API key" in error_msg or "Authorization" in error_msg:
                logger.error("API key error detected")
                logger.info("You need to set the WOLFRAM_API_KEY environment variable")
                logger.info("Get an API key from https://products.wolframalpha.com/api/")
        
        return result
    except Exception as e:
        logger.error(f"Error executing tool: {e}")
        return {"error": str(e)}

async def main():
    """Main function demonstrating manual MCP server usage for Wolfram Alpha."""
    print("\n=================================================")
    print("Manual Wolfram Alpha MCP Server Example")
    print("=================================================\n")
    
    # Define the server we want to use
    server_name = "mcp_wolfram_alpha"
    
    # Step 1: Install the server
    print("\n--- Step 1: Installing Server ---")
    success = await install_server(server_name)
    if not success:
        print("\nFailed to install server. Exiting.")
        return
    
    # Step 2: Check if Wolfram API key is set
    print("\n--- Step 2: Checking API Key ---")
    if not os.environ.get("WOLFRAM_API_KEY"):
        print("⚠️  Warning: WOLFRAM_API_KEY environment variable is not set!")
        print("You will need to set this variable to use the Wolfram Alpha server.")
        print("Get an API key from: https://products.wolframalpha.com/api/")
        
        # Uncomment to set the API key for testing
        # os.environ["WOLFRAM_API_KEY"] = "your-api-key-here"
    else:
        print("✅ WOLFRAM_API_KEY is set")
    
    try:
        # Step 3: Connect to the server
        print("\n--- Step 3: Connecting to Server ---")
        session, exit_stack = await connect_to_server(server_name)
        
        try:
            # Step 4: Execute a query on the server
            print("\n--- Step 4: Executing Query ---")
            equation = "solve x^2 + 2x - 3 = 0"
            print(f"Querying Wolfram Alpha: {equation}")
            result = await execute_wolfram_tool(session, equation)
            
            print("\n--- Results ---")
            if isinstance(result, dict) and "error" in result:
                print(f"Error: {result['error']}")
                
                # Check if it's an API key issue
                if "API key" in result["error"] or "authorization" in result["error"].lower():
                    print("\nAPI Key Error:")
                    print("1. Get a Wolfram Alpha API key from https://products.wolframalpha.com/api/")
                    print("2. Set the environment variable: export WOLFRAM_API_KEY=your-api-key")
                    print("3. Run this script again")
            else:
                print(f"Query result:")
                if isinstance(result, dict):
                    for key, value in result.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {result}")
            
        finally:
            # Step 5: Clean up
            print("\n--- Step 5: Cleaning Up ---")
            await exit_stack.aclose()
            print("Disconnected from server")
    
    except Exception as e:
        print(f"\nError: {e}")
        print("\nManual troubleshooting required:")
        print("1. Check if the server is installed correctly with 'pip list | grep mcp_wolfram_alpha'")
        print("2. Check if the wolframalpha Python package is installed with 'pip list | grep wolframalpha'")
        print("3. If wolframalpha is missing, install it with 'pip install wolframalpha'")
        print("4. Check if WOLFRAM_API_KEY is set correctly in environment variables")
        print("5. Try reinstalling the server with 'pip install --force-reinstall mcp_wolfram_alpha'")
    
    print("\n=================================================")
    print("Example completed")
    print("=================================================")

if __name__ == "__main__":
    asyncio.run(main()) 