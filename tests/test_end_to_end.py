#!/usr/bin/env python3
"""
End-to-end test for State of Mika SDK with detailed logging

This test file runs a real-world test of:
1. Receiving a query from a user
2. Claude interpreting the natural language request
3. Finding the appropriate server by capability
4. Installing the server if needed
5. Connecting to the server
6. Executing the tool
7. Returning and formatting the result

The purpose is to test the SDK with real components and APIs to ensure
proper functionality in a production environment.
Each step is logged for better visualization of the process.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from contextlib import AsyncExitStack
from typing import Dict, Any, Optional

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

# Create specialized loggers for each part of the process
interpret_logger = logging.getLogger('interpret')
registry_logger = logging.getLogger('registry')
install_logger = logging.getLogger('install')
connect_logger = logging.getLogger('connect')
execute_logger = logging.getLogger('execute')
result_logger = logging.getLogger('result')

# Import state_of_mika modules
try:
    from state_of_mika import Connector
    from state_of_mika.registry import Registry
    from state_of_mika.installer import Installer
    from state_of_mika.adapters.claude import ClaudeAdapter
except ImportError as e:
    logging.error(f"Error importing State of Mika modules: {e}")
    sys.exit(1)

# Enable auto-installation of servers
os.environ["AUTO_INSTALL_SERVERS"] = "true"

# Check if anthropic module is available
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    logging.error("Anthropic library not installed. This is required for real tests.")
    sys.exit(1)

# Create a mock ClaudeAdapter for testing
class MockClaudeAdapter:
    """A mock Claude adapter for testing that doesn't require an API key."""
    
    def __init__(self, connector=None):
        """Initialize the mock adapter."""
        self.connector = connector
        
    async def setup(self):
        """No setup needed for the mock adapter."""
        logger = logging.getLogger('mock')
        logger.info("MockClaudeAdapter initialized in testing mode")
        
    async def process_request(self, request):
        """Process a request but return errors to simulate real-world conditions.
        
        Args:
            request: The request to process
            
        Returns:
            Error response indicating that the service is not available
        """
        logger = logging.getLogger('mock')
        logger.info(f"Processing request in testing mode: {request}")
        
        # Structure the request to extract capability
        capability = "unknown"
        if "weather" in request.lower():
            capability = "weather"
            location = "Unknown"
            if "paris" in request.lower():
                location = "Paris"
            elif "london" in request.lower():
                location = "London" 
            elif "tokyo" in request.lower():
                location = "Tokyo"
            
            # Return a structured error response
            return {
                "success": False,
                "capability": capability,
                "parameters": {"location": location},
                "error": f"No server available for capability: {capability}"
            }
            
        elif "time" in request.lower():
            capability = "time"
            return {
                "success": False,
                "capability": capability,
                "error": f"No server available for capability: {capability}"
            }
            
        elif "search" in request.lower():
            capability = "search"
            return {
                "success": False, 
                "capability": capability,
                "error": f"No server available for capability: {capability}"
            }
            
        else:
            # Default error for unknown capabilities
            return {
                "success": False,
                "capability": "general",
                "error": "Unknown capability or server unavailable"
            }

# Test requests
TEST_REQUESTS = [
    "What's the weather like in Paris today?",
    "Can you tell me the current weather in London?",
    "I'd like to know the weather conditions in Tokyo."
]

async def process_llm_request(request):
    """Process an LLM request using the real components or mock components.
    
    Args:
        request: The natural language request to process
        
    Returns:
        The processed response
    """
    logger = logging.getLogger('process')
    logger.info(f"Processing LLM request: {request}")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create an AsyncExitStack for proper resource management
    async with AsyncExitStack() as stack:
        try:
            # Step 1: Initialize the components
            registry = Registry()
            installer = Installer(registry)
            connector = Connector(registry, installer)
            
            # Step 2: Load registry data
            await registry.update()
            
            # Step 3: Create and set up the adapter
            # Use MockClaudeAdapter when USE_MOCK_DATA is set
            if os.environ.get("USE_MOCK_DATA") == "true":
                adapter = MockClaudeAdapter(connector)
            else:
                adapter = ClaudeAdapter(connector=connector)
                
            await adapter.setup()
            
            # Step 4: Process the request with the adapter
            logger.info("Sending request to adapter for processing")
            response = await adapter.process_request(request)
            
            # Step 5: Log the result
            if response.get("success", False):
                result_logger.info(f"Request processing completed successfully")
            else:
                result_logger.warning(f"Request processing failed: {response.get('error', 'Unknown error')}")
            
            # Convert response to dictionary if it's not already one
            try:
                # Check if response is a CallToolResult or other custom object
                if hasattr(response, '__dict__') and not isinstance(response, dict):
                    # Convert to dictionary for JSON serialization
                    response_dict = vars(response)
                    result_logger.debug(f"Final result (converted from object): {json.dumps(response_dict, indent=2)}")
                else:
                    result_logger.debug(f"Final result: {json.dumps(response, indent=2)}")
            except (TypeError, AttributeError) as e:
                # If we can't serialize, just log the object type
                result_logger.debug(f"Final result: <Object of type {type(response).__name__} - not JSON serializable>")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            # Step 6: Clean up resources
            if 'connector' in locals():
                await connector.aclose()
            logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def run_tests():
    """Run the end-to-end tests."""
    print("\n==== Running End-to-End Tests with Real APIs ====\n")
    
    for i, request in enumerate(TEST_REQUESTS, 1):
        print(f"\nTest {i}: '{request}'")
        response = await process_llm_request(request)
        
        success = response.get("success", False)
        error = response.get("error", "Unknown error")
        capability = response.get("capability", "Unknown")
        
        print(f"Success: {success}")
        if not success:
            print(f"Error: {error}")
        print(f"Capability: {capability}")
        
        # Handle result serialization
        result = response.get('result', {})
        try:
            if hasattr(result, '__dict__') and not isinstance(result, dict):
                # Convert to dictionary for JSON serialization
                result_dict = vars(result)
                print(f"Result: {json.dumps(result_dict, indent=2)}")
            else:
                print(f"Result: {json.dumps(result, indent=2)}")
        except (TypeError, AttributeError) as e:
            # If we can't serialize, just print the object type
            print(f"Result: <Object of type {type(result).__name__} - not directly serializable>")
        
        print("-" * 50)
        
        print("\n==== End-to-End Tests Completed ====\n")

if __name__ == "__main__":
    asyncio.run(run_tests()) 