#!/usr/bin/env python
"""
Example script demonstrating the use of the State of Mika SDK with Claude.

This example shows how to:
1. Set up the Claude adapter
2. Process natural language requests
3. Chat with Claude including:
   - Tool execution
   - Image processing
   - Conversation history
   - Proper resource management

Requirements:
- State of Mika SDK
- Python 3.8+
- Anthropic Python SDK (optional, for chat mode)
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from state_of_mika
from state_of_mika import Connector
from state_of_mika.adapters.claude import ClaudeAdapter

# Try importing Anthropic to check if available
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("claude_example.log")
    ]
)
logger = logging.getLogger("ClaudeExample")

async def process_request(request: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a natural language request using the Claude adapter.
    
    Args:
        request: The natural language request
        image_path: Optional path to an image to include with the request
        
    Returns:
        Response from the request
    """
    logger.info(f"Processing request: '{request}'")
    if image_path:
        logger.info(f"Including image: {image_path}")
    
    try:
        # Create the Claude adapter
        adapter = ClaudeAdapter()
        
        # Set up the adapter
        await adapter.setup()
        
        # Check if Anthropic is available
        if not HAS_ANTHROPIC:
            logger.warning("Anthropic package not installed. Falling back to simple interpretation.")
            logger.info("To install: pip install anthropic")
        
        # Process the request using the Claude adapter
        response = await adapter.process_request(request, image_path)
        
        # Log the result
        logger.info(f"Request processed successfully: {json.dumps(response, indent=2)}")
        
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise
    finally:
        # Ensure we disconnect from any servers
        if 'adapter' in locals() and hasattr(adapter, 'connector'):
            await adapter.connector.disconnect_all()

async def interactive_chat() -> None:
    """
    Run an interactive chat session with Claude using MCP tools.
    
    This demonstrates:
    1. Maintaining conversation history
    2. Processing images with requests
    3. Executing tools based on natural language
    4. Proper resource cleanup
    """
    if not HAS_ANTHROPIC:
        logger.error("Anthropic package not installed. Interactive chat requires Claude API.")
        print("To enable chat functionality, install the Anthropic package:")
        print("  pip install anthropic")
        return
    
    try:
        # Create the Claude adapter with a persistent connector
        adapter = ClaudeAdapter()
        
        # Run the interactive chat using the adapter's built-in method
        await adapter.interactive_chat()
    except Exception as e:
        logger.error(f"Error in interactive chat: {e}")
    finally:
        # Ensure we disconnect from any servers when done
        if 'adapter' in locals() and hasattr(adapter, 'connector'):
            await adapter.connector.disconnect_all()

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Claude Example for State of Mika SDK")
    parser.add_argument("--request", type=str, help="Natural language request to process")
    parser.add_argument("--image", type=str, help="Path to an image to include with the request")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive chat mode")
    return parser.parse_args()

async def main():
    """
    Main entry point for the example.
    """
    args = parse_args()
    
    if args.interactive:
        # Interactive chat mode
        await interactive_chat()
    elif args.request:
        # Process a single request
        response = await process_request(args.request, args.image)
        
        # Display the result
        if response.get("success", False):
            print(f"\nCapability: {response['capability']}")
            print(f"Tool: {response['tool']}")
            print(f"Parameters: {json.dumps(response['parameters'], indent=2)}")
            print(f"\nResult:\n{json.dumps(response['result'], indent=2)}")
        else:
            print(f"\nError: {response.get('error', 'Unknown error')}")
    else:
        # No arguments provided, show help
        print("Please specify a request or use interactive mode.")
        print("Examples:")
        print("  --request 'What's the weather in Paris?'")
        print("  --request 'What's in this image?' --image path/to/image.jpg")
        print("  --interactive")

if __name__ == "__main__":
    asyncio.run(main()) 