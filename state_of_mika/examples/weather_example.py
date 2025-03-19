#!/usr/bin/env python
"""
Weather Example

This example demonstrates using the State of Mika SDK to get weather information.
It shows how to:
1. Set up the Connector
2. Find and connect to a weather MCP server
3. Execute a weather tool
4. Process the results
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the parent directory to the path
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from state_of_mika import Connector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_weather(location: str = "New York"):
    """
    Get weather information for a location.
    
    Args:
        location: Location to get weather for
    """
    logger.info(f"Getting weather for {location}")
    
    # Create a connector
    connector = Connector()
    
    try:
        # Set up the connector
        await connector.setup()
        
        # Find and connect to a weather server
        server_id, client = await connector.find_and_connect("weather")
        logger.info(f"Connected to server: {server_id}")
        
        # List available tools
        tools = await client.list_tools()
        logger.info(f"Available tools: {[tool['name'] for tool in tools]}")
        
        # Find a weather tool
        weather_tool = next((tool for tool in tools if "weather" in tool["name"].lower()), None)
        
        if not weather_tool:
            logger.error("No weather tool found")
            return
            
        tool_name = weather_tool["name"]
        logger.info(f"Using tool: {tool_name}")
        
        # Execute the weather tool
        result = await client.call_tool(tool_name, {"location": location})
        
        # Print the results
        logger.info("Weather Results:")
        logger.info(f"Location: {location}")
        if "temperature" in result:
            logger.info(f"Temperature: {result['temperature']}°C")
        if "description" in result:
            logger.info(f"Condition: {result['description']}")
        if "humidity" in result:
            logger.info(f"Humidity: {result['humidity']}%")
        
        # Print the full result
        logger.info(f"Full result: {result}")
        
    except Exception as e:
        logger.error(f"Error getting weather: {e}")
    finally:
        # Disconnect from all servers
        await connector.disconnect_all()

if __name__ == "__main__":
    # Get location from command line arguments if provided
    location = sys.argv[1] if len(sys.argv) > 1 else "New York"
    
    # Run the example
    asyncio.run(get_weather(location)) 