#!/usr/bin/env python3
"""
Test script to demonstrate the complete flow with Claude as the deciding layer.

This script shows:
1. How Claude analyzes user requests to determine capabilities
2. How Claude analyzes errors to provide helpful suggestions
"""

import os
import ssl
import asyncio
import logging
import json
import aiohttp
from dotenv import load_dotenv

# Before importing our modules, set up the SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Monkey patch aiohttp.ClientSession to use our SSL context
original_init = aiohttp.ClientSession.__init__

def patched_init(self, *args, **kwargs):
    if 'connector' not in kwargs:
        kwargs['connector'] = aiohttp.TCPConnector(ssl=ssl_context)
    original_init(self, *args, **kwargs)

aiohttp.ClientSession.__init__ = patched_init

# Now import our modules
from state_of_mika.som_agent import SoMAgent

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_som_agent")

async def test_som_agent():
    """Test the SoMAgent with a variety of requests and error scenarios."""
    print("\n===== Testing State of Mika Agent with Claude =====\n")
    
    # Create the agent with standard setup
    # This will use the updated ClaudeAdapter with SSL verification disabled
    agent = SoMAgent(auto_install=True)
    await agent.setup()
    
    # Display server configurations for reference
    print("\n===== Available Servers and Tools =====")
    server_configs = agent.claude_adapter.server_configs
    if server_configs and "servers" in server_configs:
        for server in server_configs["servers"]:
            print(f"\nServer: {server.get('name')}")
            print(f"Capabilities: {', '.join(server.get('capabilities', []))}")
            print("Available tools:")
            for tool_name, tool_info in server.get("schema", {}).items():
                param_info = ', '.join([f"{p}" for p in tool_info.get("parameters", {}).keys()])
                print(f"  - {tool_name} ({param_info})")
    else:
        print("No server configurations available.")
    print("\n===== End of Server Configurations =====\n")
    
    # Test cases
    test_cases = [
        {
            "name": "Weather request (success case)",
            "request": "What's the weather like in Paris today?",
            "expected_capability": "weather",
            "expected_tool": "get_hourly_weather"  # Updated to match actual tool name
        },
        {
            "name": "Weather request without API key (error case)",
            "request": "What's the weather like in London?",
            "expected_capability": "weather",
            "expected_tool": "get_hourly_weather",  # Updated to match actual tool name
            "unset_keys": ["ACCUWEATHER_API_KEY"]  # Temporarily unset this key
        },
        {
            "name": "Non-existent capability",
            "request": "Solve this complex math equation: 3x^2 + 2x - 5 = 0",
            "expected_capability": "math"  # We don't have a math capability
        }
    ]
    
    # Run the tests
    for i, test in enumerate(test_cases, 1):
        print(f"\n>> Test {i}: {test['name']}")
        print(f"Request: {test['request']}")
        
        # Temporarily unset specified environment variables
        original_values = {}
        for key in test.get("unset_keys", []):
            original_values[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
                print(f"Temporarily unset {key} for testing.")
        
        try:
            # Process the request
            result = await agent.process_request(test["request"])
            
            # Print the result
            print("\nResult:")
            print(f"Status: {result.get('status')}")
            
            if result.get("status") == "success":
                print("✅ Success!")
                print(f"Capability: {result.get('capability')}")
                print(f"Tool: {result.get('tool_name')}")
                print("Result: ", end="")
                
                # Format the result nicely
                try:
                    if isinstance(result.get("result"), dict):
                        print(json.dumps(result.get("result"), indent=2))
                    else:
                        print(result.get("result"))
                except:
                    print(result.get("result"))
            else:
                print("❌ Error!")
                print(f"Error: {result.get('error')}")
                print(f"Error Type: {result.get('error_type', 'Unknown')}")
                print(f"Explanation: {result.get('explanation', 'No explanation provided')}")
                print(f"Suggestion: {result.get('suggestion', 'No suggestion provided')}")
                
            # Check if the capability matched the expected one
            if "capability" in result and test.get("expected_capability"):
                if result["capability"] == test["expected_capability"]:
                    print(f"✅ Correct capability determined: {result['capability']}")
                else:
                    print(f"❌ Incorrect capability: {result['capability']}, expected: {test['expected_capability']}")
                    
            # Check if the tool matched the expected one, if specified
            if "tool_name" in result and test.get("expected_tool"):
                if result["tool_name"] == test["expected_tool"]:
                    print(f"✅ Correct tool determined: {result['tool_name']}")
                else:
                    print(f"❌ Incorrect tool: {result['tool_name']}, expected: {test['expected_tool']}")
                    
        except Exception as e:
            print(f"\n❌ Unexpected test exception: {str(e)}")
        
        # Restore environment variables
        for key, value in original_values.items():
            if value is not None:
                os.environ[key] = value
                print(f"Restored {key} environment variable.")
    
    # Clean up
    await agent.aclose()
    print("\n===== Testing Completed =====")

if __name__ == "__main__":
    asyncio.run(test_som_agent()) 