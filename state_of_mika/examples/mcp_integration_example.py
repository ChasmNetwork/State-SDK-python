#!/usr/bin/env python
"""
MCP Integration Example for State of Mika SDK

This example demonstrates the enhanced MCP integration features of the State of Mika SDK:
1. Proper lifecycle management using AsyncExitStack
2. Context manager-based resource handling
3. Multimodal support with image processing
4. Conversation history for contextual interactions
5. Custom server launch and execution

Requirements:
- State of Mika SDK
- Python 3.8+
- Anthropic Python SDK (for Claude features)
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from state_of_mika
from state_of_mika import Connector
from state_of_mika.registry import Registry 
from state_of_mika.installer import Installer
from state_of_mika.adapters.claude import ClaudeAdapter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mcp_integration.log")
    ]
)
logger = logging.getLogger("MCPIntegration")

async def demonstrate_connector_lifecycle():
    """
    Demonstrate proper lifecycle management with the Connector.
    
    This shows how to:
    1. Create and set up a connector
    2. Use context managers for safe resource handling
    3. Execute tools with proper cleanup
    """
    logger.info("=== Demonstrating Connector Lifecycle Management ===")
    
    # Create connector components
    registry = Registry()
    installer = Installer(registry)
    
    # Create the connector with these components
    connector = Connector(registry, installer)
    
    # Set up the connector
    await connector.setup()
    
    try:
        # Example 1: Using context manager for automatic cleanup
        logger.info("Example 1: Using connect_session context manager")
        
        try:
            # This context manager automatically handles server connection and disconnection
            async with connector.connect_session("weather") as (server_name, client):
                logger.info(f"Connected to server: {server_name}")
                
                # List available tools
                tools = await client.list_tools()
                logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
                
                # Execute a tool
                result = await client.call_tool("get_weather", {"location": "Paris"})
                logger.info(f"Weather result: {json.dumps(result, indent=2)}")
                
                # Context manager will automatically disconnect when we exit
                logger.info("Exiting context, connection will be cleaned up automatically")
        except Exception as e:
            logger.error(f"Error in connect_session example: {e}")
        
        # Example 2: Manual connection with disconnect
        logger.info("\nExample 2: Manual connection with explicit disconnect")
        
        try:
            # Find and connect to a search server
            server_name, client = await connector.find_and_connect("search")
            logger.info(f"Connected to server: {server_name}")
            
            # Execute a search tool
            result = await client.call_tool("web_search", {"query": "Model Context Protocol"})
            logger.info(f"Search result: {json.dumps(result, indent=2)}")
            
            # Manually disconnect
            await connector.disconnect(server_name)
            logger.info(f"Manually disconnected from server: {server_name}")
        except Exception as e:
            logger.error(f"Error in manual connection example: {e}")
            
        # Example 3: Execute method that handles connections internally
        logger.info("\nExample 3: Using execute() method for simplified tool execution")
        
        try:
            # The execute method handles finding a server, connecting, and executing the tool
            result = await connector.execute(
                capability="weather",
                tool_name="get_weather",
                parameters={"location": "Tokyo"}
            )
            logger.info(f"Execute result: {json.dumps(result, indent=2)}")
        except Exception as e:
            logger.error(f"Error in execute example: {e}")
        
    finally:
        # Clean up all connections
        logger.info("\nCleaning up all connections")
        await connector.disconnect_all()
        logger.info("All connections cleaned up")

async def demonstrate_claude_multimodal():
    """
    Demonstrate multimodal capabilities with the Claude adapter.
    
    This shows how to:
    1. Process text and images together
    2. Maintain conversation history
    3. Reset history when needed
    """
    logger.info("\n=== Demonstrating Claude Multimodal Support ===")
    
    # Get an optional image path from the environment or use a default
    image_path = os.environ.get("TEST_IMAGE_PATH", None)
    if image_path and os.path.exists(image_path):
        logger.info(f"Using test image: {image_path}")
    else:
        logger.info("No test image available, continuing with text-only examples")
        image_path = None
    
    # Create a Claude adapter
    adapter = ClaudeAdapter()
    
    try:
        # Set up the adapter
        await adapter.setup()
        
        # Example 1: Process a text request
        logger.info("Example 1: Processing a text request")
        text_response = await adapter.process_request("What's the weather like in Paris?")
        logger.info(f"Text response: {json.dumps(text_response, indent=2)}")
        
        # Example 2: Process a request with an image (if available)
        if image_path:
            logger.info("\nExample 2: Processing a request with an image")
            image_response = await adapter.process_request(
                "What can you tell me about this image?",
                image_path=image_path
            )
            logger.info(f"Image response: {json.dumps(image_response, indent=2)}")
        
        # Example 3: Chat with conversation history
        logger.info("\nExample 3: Chat with conversation history")
        
        # First message
        first_response = await adapter.chat("What's the capital of France?")
        logger.info(f"First response: {first_response}")
        
        # Follow-up that relies on conversation history
        followup_response = await adapter.chat("What's the population of that city?")
        logger.info(f"Follow-up response: {followup_response}")
        
        # Reset the chat history
        await adapter.reset_chat()
        logger.info("Chat history reset")
        
        # New conversation
        new_response = await adapter.chat("Tell me about the weather in London")
        logger.info(f"New conversation response: {new_response}")
        
    except Exception as e:
        logger.error(f"Error in Claude multimodal example: {e}")
    finally:
        # Clean up resources
        await adapter.connector.disconnect_all()
        logger.info("Claude adapter resources cleaned up")

async def demonstrate_custom_server_integration():
    """
    Demonstrate integration with custom MCP servers.
    
    This shows how to:
    1. Work with custom server launch parameters
    2. Configure server environment variables
    3. List and execute server-specific tools
    """
    logger.info("\n=== Demonstrating Custom Server Integration ===")
    
    # Create a connector
    connector = Connector()
    
    # Set up the connector
    await connector.setup()
    
    try:
        # Example 1: Get server launch info
        logger.info("Example 1: Using _get_server_launch_info")
        
        # Get some server data
        server_data = {
            "name": "example_server",
            "installation": {
                "type": "pip",
                "package": "example-mcp-server"
            }
        }
        
        # Get the launch info
        command, args, env = connector._get_server_launch_info("example_server", server_data)
        logger.info(f"Server launch command: {command}")
        logger.info(f"Server launch args: {args}")
        
        # Example 2: List tools from a server (if installed)
        logger.info("\nExample 2: Listing tools from a server")
        
        try:
            # Search for weather servers in registry
            weather_servers = connector.registry.search_by_capability("weather")
            
            if weather_servers:
                server_name = weather_servers[0]["name"]
                logger.info(f"Found weather server: {server_name}")
                
                # List tools from the server
                tools = await connector.list_server_tools(server_name)
                logger.info(f"Tools from {server_name}: {json.dumps(tools, indent=2)}")
            else:
                logger.info("No weather servers found in registry")
        except Exception as e:
            logger.error(f"Error listing server tools: {e}")
            
    finally:
        # Clean up all connections
        await connector.disconnect_all()
        logger.info("All connections cleaned up")

async def run_full_demo():
    """
    Run all demonstration functions in sequence.
    """
    logger.info("Starting MCP Integration Demo")
    
    try:
        # Demonstrate connector lifecycle management
        await demonstrate_connector_lifecycle()
        
        # Demonstrate Claude multimodal support
        await demonstrate_claude_multimodal()
        
        # Demonstrate custom server integration
        await demonstrate_custom_server_integration()
        
    except Exception as e:
        logger.error(f"Error in demo: {e}")
    
    logger.info("MCP Integration Demo completed")

if __name__ == "__main__":
    asyncio.run(run_full_demo()) 