# MikaAdapter for State of Mika SDK

> **Note**: This documentation has been updated to reflect the current state of the State of Mika SDK. The `ClaudeAdapter` has been replaced by the `MikaAdapter`, which provides improved functionality for integrating with Claude and MCP servers.

This document explains how to use the MikaAdapter with the State of Mika SDK to enable natural language interactions with MCP servers.

## Overview

The MikaAdapter serves as a bridge between the Claude language model and MCP servers, allowing Claude to:

1. Understand natural language requests
2. Determine the required capabilities and tools
3. Connect to appropriate MCP servers
4. Execute tools and return results
5. Format responses in a user-friendly way

## Features

- **Natural Language Processing**: Convert user requests into structured tool calls
- **Multimodal Support**: Process images alongside text
- **Conversation History**: Maintain context across multiple interactions
- **Interactive Chat Mode**: Engage in back-and-forth conversations
- **Fallback Interpretation**: Basic functionality even without Claude API

## Requirements

- State of Mika SDK
- Python 3.8+
- Anthropic API key (set as `ANTHROPIC_API_KEY` environment variable)
- `anthropic` Python package (optional, but recommended)

## Installation

```bash
# Install the State of Mika SDK
pip install state-of-mika

# Install the Anthropic Python client for full functionality
pip install anthropic
```

## Basic Usage

```python
import asyncio
from state_of_mika import SoMAgent

async def process_request():
    # Create the SoM Agent (which uses MikaAdapter internally)
    agent = SoMAgent()
    
    # Set up the agent
    await agent.setup()
    
    try:
        # Process a natural language request
        response = await agent.process_request("What's the weather like in Tokyo today?")
        
        # Check if the request was successful
        if response["status"] == "success":
            print(f"Capability: {response['capability']}")
            print(f"Tool: {response['tool_name']}")
            print(f"Result: {response['result']}")
        else:
            print(f"Error: {response['error']}")
    finally:
        # Clean up resources
        await agent.aclose()

if __name__ == "__main__":
    asyncio.run(process_request())
```

## Working with the MikaAdapter Directly

If you need to use the MikaAdapter directly for more advanced scenarios:

```python
import asyncio
from state_of_mika.mika_adapter import MikaAdapter

async def analyze_request():
    # Create the MikaAdapter
    adapter = MikaAdapter()
    
    # Load server configurations
    await adapter.load_server_configs()
    
    # Analyze a request
    result = await adapter.analyze_request("What's the weather like in Tokyo today?")
    
    print(f"Capability: {result['capability']}")
    print(f"Tool: {result['tool_name']}")
    print(f"Parameters: {result['parameters']}")

if __name__ == "__main__":
    asyncio.run(analyze_request())
```

## Working with Images

For image analysis, you can use the SoMAgent with the appropriate capability:

```python
import asyncio
from state_of_mika import SoMAgent

async def process_image_request():
    # Create the SoM Agent
    agent = SoMAgent()
    
    # Set up the agent
    await agent.setup()
    
    try:
        # Process a request that includes an image
        response = await agent.process_request(
            "What's in this image?",
            context={"image_path": "path/to/image.jpg"}
        )
        
        print(f"Capability: {response['capability']}")
        print(f"Tool: {response['tool_name']}")
        print(f"Result: {response['result']}")
    finally:
        # Clean up resources
        await agent.aclose()

if __name__ == "__main__":
    asyncio.run(process_image_request())
```

## Interactive Chat

```python
import asyncio
from state_of_mika import SoMAgent

async def interactive_chat():
    # Create the SoM Agent
    agent = SoMAgent()
    
    # Set up the agent
    await agent.setup()
    
    # Start a conversation
    print("\nChat with Claude (type 'exit' to quit):")
    
    try:
        while True:
            # Get user input
            user_input = input("\nYou: ")
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit"]:
                break
                
            # Process the request
            response = await agent.process_request(user_input)
            
            # Display the response
            if response["status"] == "success":
                print(f"\nClaude: {response['result']}")
            else:
                print(f"\nError: {response['error']}")
    finally:
        # Clean up resources
        await agent.aclose()

if __name__ == "__main__":
    asyncio.run(interactive_chat())
```

## Customization

### Using a Different Claude Model

```python
from state_of_mika import SoMAgent

agent = SoMAgent(model="claude-3-haiku-20240307")
```

### Using Your Own Claude Client

```python
import anthropic
from state_of_mika.mika_adapter import MikaAdapter

# Create your own Claude client
claude = anthropic.Anthropic(api_key="your_api_key")

# Pass it to the adapter
adapter = MikaAdapter(api_key="your_api_key")
```

### Using a Custom Connector

```python
from state_of_mika import Connector, SoMAgent

# Create a custom connector
connector = Connector()

# Create a SoMAgent with the custom connector
agent = SoMAgent(connector=connector)
```

## Advanced Usage: Error Analysis

```python
import asyncio
from state_of_mika.mika_adapter import MikaAdapter

async def analyze_error():
    adapter = MikaAdapter()
    
    # Sample error
    error = {
        "status": "error",
        "message": "API key is missing or invalid"
    }
    
    # Analyze the error
    result = await adapter.analyze_error(
        error, 
        original_request="What's the weather in Tokyo?",
        context={"capability": "weather"}
    )
    
    print(f"Error Type: {result['error_type']}")
    print(f"Explanation: {result['explanation']}")
    print(f"Suggestion: {result['suggestion']}")

if __name__ == "__main__":
    asyncio.run(analyze_error())
```

## Error Handling

```python
import asyncio
from state_of_mika import SoMAgent

async def handle_errors():
    agent = SoMAgent()
    await agent.setup()
    
    try:
        # Process a request that might fail
        try:
            response = await agent.process_request("Find data in a non-existent database")
            
            if response["status"] != "success":
                print(f"Request failed: {response['error']}")
                print(f"Suggestion: {response['suggestion']}")
                # Implement fallback behavior
        except Exception as e:
            print(f"Error: {e}")
    finally:
        await agent.aclose()

if __name__ == "__main__":
    asyncio.run(handle_errors())
``` 