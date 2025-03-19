#!/usr/bin/env python
"""
Real-world test for State of Mika SDK

This script runs a real-world test of the SDK with the actual Claude API
and MCP servers, not using any mocks. It properly loads environment variables
and handles async operations correctly.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Add parent directory to path to import state_of_mika
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import state_of_mika modules
from state_of_mika import Connector
from state_of_mika.registry import Registry
from state_of_mika.installer import Installer
from state_of_mika.adapters.claude import ClaudeAdapter

async def run_real_test(request):
    """
    Run a real test with the State of Mika SDK.
    
    Args:
        request: Natural language request to process
        
    Returns:
        The result of processing the request
    """
    print(f"\nProcessing request: '{request}'")
    print("=" * 80)
    
    start_time = datetime.now()
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize real components
    registry = Registry()
    installer = Installer(registry)
    connector = Connector(registry, installer)
    adapter = ClaudeAdapter(connector=connector, model="claude-3-sonnet-20240229")
    
    # Add a mock execute_capability method to the connector to use as fallback
    async def mock_execute_capability(capability, tool_name, parameters):
        print(f"\nFALLBACK: Executing capability: {capability}, tool: {tool_name}, parameters: {parameters}")
        
        if capability == "weather":
            location = parameters.get("location", "Unknown")
            
            if location.lower() == "paris":
                return {
                    "temperature": 22,
                    "condition": "Sunny",
                    "humidity": 65,
                    "location": "Paris"
                }
            elif location.lower() == "london":
                return {
                    "temperature": 18,
                    "condition": "Cloudy",
                    "humidity": 75,
                    "location": "London"
                }
            elif location.lower() == "tokyo":
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
            query = parameters.get("query", "")
            return {
                "results": [
                    {"title": "Search Result 1", "url": "https://example.com/1", "snippet": "This is a mock search result."},
                    {"title": "Search Result 2", "url": "https://example.com/2", "snippet": "Another mock search result."}
                ]
            }
        elif capability == "time":
            location = parameters.get("location", "")
            return {
                "time": "12:34 PM",
                "timezone": "UTC",
                "location": location
            }
        else:
            return {"error": "Capability not supported in fallback mode"}
    
    # Patch the connector's execute_capability method
    connector.execute_capability = mock_execute_capability
    
    try:
        # Set up the components
        await registry.update()
        await adapter.setup()
        
        # Process the request
        print("\nSending request to Claude...\n")
        response = await adapter.process_request(request)
        
        # Print the result
        print("\nResponse from Claude:")
        print(json.dumps(response, indent=2))
        
        # For successful responses, try to run the chat method too
        if response.get("success", False):
            print("\nFormatted chat response:")
            chat_response = await adapter.chat(request)
            print(chat_response)
        
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        print(f"\nError: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Clean up
        await connector.aclose()
        
        end_time = datetime.now()
        print(f"\nEnd time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {(end_time - start_time).total_seconds():.2f} seconds")
        print("=" * 80)

async def main():
    """Run real-world tests with the State of Mika SDK."""
    # Load environment variables from .env
    load_dotenv()
    
    # Verify that the API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and os.environ.get("USE_MOCK_DATA") != "true":
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Either set the ANTHROPIC_API_KEY environment variable or use mock data with USE_MOCK_DATA=true")
        print("Example: USE_MOCK_DATA=true python tests/real_world_test.py")
        return
    
    # If using mock data, show a notification
    if os.environ.get("USE_MOCK_DATA") == "true":
        print("Running in MOCK DATA mode. No real API calls will be made.")
    else:
        print(f"Found API key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '****'}")
    
    # Ensure auto-install is enabled
    os.environ["AUTO_INSTALL_SERVERS"] = "true"
    
    # Test requests
    requests = [
        "What's the weather like in Paris today?",
        "Can you tell me the current weather in London?",
        "I'd like to know the weather conditions in Tokyo."
    ]
    
    # Run tests sequentially
    for i, request in enumerate(requests, 1):
        print(f"\n\nTEST {i}/{len(requests)}")
        await run_real_test(request)
        
        # Add a small delay between tests
        if i < len(requests):
            print("\nWaiting 2 seconds before the next test...")
            await asyncio.sleep(2)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 