#!/usr/bin/env python3
"""
State of Mika SDK - Quick Start Example

This example demonstrates the basic usage of the State of Mika SDK (SoM)
to process natural language requests and access different capabilities.
"""

import os
import asyncio
import logging
from state_of_mika import SoMAgent

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("som_example")

async def process_request(query):
    """Process a natural language request using the SoM Agent."""
    # Create the agent with auto-installation enabled
    agent = SoMAgent(auto_install=True)
    
    # Set up the agent (loads registry, etc.)
    await agent.setup()
    
    try:
        logger.info(f"Processing request: {query}")
        
        # Process the natural language request
        result = await agent.process_request(query)
        
        # Check if the request was successful
        if result.get("status") == "success":
            logger.info(f"Request successful!")
            logger.info(f"Capability used: {result.get('capability')}")
            logger.info(f"Tool used: {result.get('tool_name')}")
            
            # Print the result
            print("\n--- Result ---")
            print_result(result.get("result"))
            
            return result.get("result")
        else:
            # Handle errors
            logger.error(f"Request failed: {result.get('error')}")
            logger.error(f"Error type: {result.get('error_type')}")
            
            # Print suggestions
            print("\n--- Error Information ---")
            print(f"Error: {result.get('error')}")
            print(f"Type: {result.get('error_type')}")
            print(f"Suggestion: {result.get('suggestion')}")
            
            if result.get("missing_api_key"):
                print(f"\nMissing API key: {result.get('missing_api_key')}")
                print("Set this environment variable to fix the issue.")
            
            return None
    finally:
        # Always clean up resources
        await agent.aclose()

def print_result(result):
    """Pretty print the result based on its type."""
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"{key}: {value}")
    elif isinstance(result, list):
        for i, item in enumerate(result, 1):
            print(f"{i}. {item}")
    else:
        print(result)

async def main():
    """Run the example with different capability requests."""
    print("\n===== State of Mika SDK Example =====\n")
    
    # List of example requests to demonstrate different capabilities
    example_requests = [
        "What's the weather like in Tokyo today?",
        "Search for the latest news about artificial intelligence",
        "What time is it in New York?",
        "Solve the equation x^2 + 2x - 3 = 0"
    ]
    
    # Allow the user to choose an example or enter their own
    print("Example requests:")
    for i, req in enumerate(example_requests, 1):
        print(f"{i}. {req}")
    print("5. Enter your own request")
    
    choice = input("\nEnter your choice (1-5): ")
    
    try:
        choice_num = int(choice)
        if 1 <= choice_num <= 4:
            request = example_requests[choice_num - 1]
        elif choice_num == 5:
            request = input("\nEnter your request: ")
        else:
            print("Invalid choice. Using the first example.")
            request = example_requests[0]
    except ValueError:
        print("Invalid input. Using the first example.")
        request = example_requests[0]
    
    print(f"\nProcessing request: '{request}'")
    await process_request(request)
    
    print("\n===== Example Complete =====")

if __name__ == "__main__":
    # Check if Anthropic API key is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️ Warning: ANTHROPIC_API_KEY environment variable is not set!")
        print("The SDK requires an Anthropic API key to analyze requests.")
        print("Get an API key from: https://www.anthropic.com/product")
        print("Then set it with: export ANTHROPIC_API_KEY='your_key_here'")
    
    # Run the async main function
    asyncio.run(main()) 