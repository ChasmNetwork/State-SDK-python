#!/usr/bin/env python3
"""
Test script to demonstrate the complete flow with Mika as the deciding layer.

This script shows:
1. How Mika analyzes user requests to determine capabilities
2. How Mika analyzes errors to provide helpful suggestions
"""

import os
import ssl
import asyncio
import logging
import json
import aiohttp
from dotenv import load_dotenv

# Force auto-installation of servers
os.environ["AUTO_INSTALL_SERVERS"] = "true"

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # Use colorful formatting for better visibility in presentations
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("test_som_agent")

# Add a separator function for better visual separation in logs
def log_separator(title):
    """Print a visually distinct separator with a title."""
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"    {title}")
    print(f"{separator}\n")

async def test_som_agent():
    """Test the SoMAgent with a variety of requests and error scenarios."""
    log_separator("Testing State of Mika Agent with Claude")
    
    print("🔧 Initializing SoMAgent with auto-installation enabled...")
    
    # Create the agent with standard setup
    # This will use the MikaAdapter with SSL verification disabled
    agent = SoMAgent(auto_install=True)
    print("⚙️ Setting up agent and loading registry...")
    await agent.setup()
    
    # Display server configurations for reference
    log_separator("Available Servers and Tools")
    server_configs = agent.mika_adapter.server_configs
    if server_configs and "servers" in server_configs:
        for server in server_configs["servers"]:
            print(f"\n📦 Server: {server.get('name')}")
            print(f"📋 Capabilities: {', '.join(server.get('capabilities', []))}")
            print("🔧 Available tools:")
            for tool_name, tool_info in server.get("schema", {}).items():
                param_info = ', '.join([f"{p}" for p in tool_info.get("parameters", {}).keys()])
                print(f"  - 🛠️ {tool_name} ({param_info})")
    else:
        print("❌ No server configurations available.")
    print("\n")
    
    # Test cases
    test_cases = [
        {
            "name": "Weather request (success case)",
            "request": "What's the weather like in Paris today?",
            "expected_capability": "weather",
            "expected_tool": "get_hourly_weather"  # Updated to match actual tool name
        },
        {
            "name": "Weather request with API key error",
            "request": "What's the weather like in London?",
            "expected_capability": "weather",
            "expected_tool": "get_hourly_weather",  # Updated to match actual tool name
            "unset_keys": ["ACCUWEATHER_API_KEY"],  # Temporarily unset this key
            "show_detailed_error": True  # Flag to show detailed error analysis
        },
        {
            "name": "Wolfram Alpha request with missing dependency",
            "request": "Solve the equation x^2 + 2x - 3 = 0",
            "expected_capability": "wolfram_alpha",
            "expected_tool": "query",
            "show_detailed_error": True
        },
        {
            "name": "Non-existent capability",
            "request": "Teleport me to Mars",
            "expected_capability": "teleportation"  # We don't have this capability
        }
    ]
    
    # Run the tests
    for i, test in enumerate(test_cases, 1):
        log_separator(f"Test {i}: {test['name']}")
        print(f"🔍 Request: {test['request']}")
        
        # Temporarily unset specified environment variables
        original_values = {}
        for key in test.get("unset_keys", []):
            original_values[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
                print(f"🔄 Temporarily unset {key} for testing.")
                print(f"🔍 Testing how system responds when {key} is missing...")
        
        try:
            # Process the request
            print("\n⚙️ Processing request through Claude and State of Mika...\n")
            
            # Normal processing
            result = await agent.process_request(test["request"])
            
            # Print the result
            print("\n📋 Result:")
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
                
                # Show detailed error information if available and requested
                if test.get("show_detailed_error", False):
                    log_separator("Detailed Error Analysis")
                    print(f"🔍 Error Type: {result.get('error_type', 'Unknown')}")
                    print(f"📋 Explanation: {result.get('explanation', 'No explanation provided')}")
                    print(f"💡 Suggestion: {result.get('suggestion', 'No suggestion provided')}")
                    print(f"🔧 Requires User Action: {result.get('requires_user_action', True)}")
                    
                    # Show missing API key information if available
                    if result.get("missing_api_key"):
                        print(f"\n🔑 Missing API Key: {result.get('missing_api_key')}")
                        print(f"   Environment Variable Needed: export {result.get('missing_api_key')}=your_api_key_here")
                    
                    # Show missing dependency information if available
                    if result.get("missing_dependency"):
                        print(f"\n📦 Missing Dependency: {result.get('missing_dependency')}")
                        print(f"   Installation Command: pip install {result.get('missing_dependency')}")
                    
                    # Show API key hint
                    if "api key" in result.get('error', '').lower() or "api key" in result.get('explanation', '').lower():
                        print("\n🔑 API Key Issue Detected!")
                        if "ACCUWEATHER_API_KEY" in test.get("unset_keys", []):
                            print("   This test deliberately removed the ACCUWEATHER_API_KEY to simulate this error.")
                            print("   To fix in a real scenario: export ACCUWEATHER_API_KEY=your_api_key_here")
                else:
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
                print(f"🔄 Restored {key} environment variable.")
    
    # Clean up
    await agent.aclose()
    log_separator("Testing Completed")

if __name__ == "__main__":
    asyncio.run(test_som_agent()) 