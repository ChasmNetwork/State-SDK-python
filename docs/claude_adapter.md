# Claude Adapter for State of Mika SDK

This document explains how to use the Claude adapter with the State of Mika SDK to enable natural language interactions with MCP servers.

## Overview

The Claude adapter serves as a bridge between the Claude language model and MCP servers, allowing Claude to:

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
from state_of_mika.adapters.claude import ClaudeAdapter

async def process_request():
    # Create the Claude adapter
    adapter = ClaudeAdapter()
    
    # Set up the adapter
    await adapter.setup()
    
    try:
        # Process a natural language request
        response = await adapter.process_request("What's the weather like in Tokyo today?")
        
        # Check if the request was successful
        if response["success"]:
            print(f"Capability: {response['capability']}")
            print(f"Tool: {response['tool']}")
            print(f"Parameters: {response['parameters']}")
            print(f"Result: {response['result']}")
        else:
            print(f"Error: {response['error']}")
    finally:
        # Clean up resources
        await adapter.connector.disconnect_all()

if __name__ == "__main__":
    asyncio.run(process_request())
```

## Working with Images

```python
import asyncio
from state_of_mika.adapters.claude import ClaudeAdapter

async def process_image_request():
    # Create the Claude adapter
    adapter = ClaudeAdapter()
    
    # Set up the adapter
    await adapter.setup()
    
    try:
        # Process a request that includes an image
        response = await adapter.process_request(
            "What's in this image?",
            image_path="path/to/image.jpg"
        )
        
        print(f"Capability: {response['capability']}")
        print(f"Tool: {response['tool']}")
        print(f"Result: {response['result']}")
    finally:
        # Clean up resources
        await adapter.connector.disconnect_all()

if __name__ == "__main__":
    asyncio.run(process_image_request())
```

## Interactive Chat

```python
import asyncio
from state_of_mika.adapters.claude import ClaudeAdapter

async def interactive_chat():
    # Create the Claude adapter
    adapter = ClaudeAdapter()
    
    # Run the interactive chat session
    await adapter.interactive_chat()

if __name__ == "__main__":
    asyncio.run(interactive_chat())
```

The interactive chat provides a command-line interface where you can:

- Chat with Claude using natural language
- Include images with requests using the `--image` flag
- Reset the conversation history with `reset`
- Exit the chat with `exit`

## Customization

### Using a Different Claude Model

```python
adapter = ClaudeAdapter(model="claude-3-haiku-20240307")
```

### Using Your Own Claude Client

```python
import anthropic

# Create your own Claude client
claude = anthropic.Anthropic(api_key="your_api_key")

# Pass it to the adapter
adapter = ClaudeAdapter(claude_client=claude)
```

### Using a Custom Connector

```python
from state_of_mika import Connector

# Create a custom connector
connector = Connector()

# Pass it to the adapter
adapter = ClaudeAdapter(connector=connector)
```

## Advanced Usage: Chat with History

```python
import asyncio
from state_of_mika.adapters.claude import ClaudeAdapter

async def chat_with_history():
    adapter = ClaudeAdapter()
    await adapter.setup()
    
    try:
        # First request
        response1 = await adapter.chat("What's the weather in Paris?")
        print(f"Claude: {response1}")
        
        # Follow-up question that references the previous question
        response2 = await adapter.chat("How about in London?")
        print(f"Claude: {response2}")
        
        # Reset the chat history when needed
        await adapter.reset_chat()
    finally:
        await adapter.connector.disconnect_all()

if __name__ == "__main__":
    asyncio.run(chat_with_history())
```

## Error Handling

```python
import asyncio
from state_of_mika.adapters.claude import ClaudeAdapter

async def handle_errors():
    adapter = ClaudeAdapter()
    await adapter.setup()
    
    try:
        # Process a request that might fail
        try:
            response = await adapter.process_request("Find data in a non-existent database")
            
            if not response["success"]:
                print(f"Request failed: {response['error']}")
                # Implement fallback behavior
        except Exception as e:
            print(f"Error: {e}")
    finally:
        await adapter.connector.disconnect_all()

if __name__ == "__main__":
    asyncio.run(handle_errors())
```

## Comparison: process_request vs. chat

The Claude adapter provides two main methods for processing user requests:

1. **`process_request`**: Focuses on executing a specific tool and returning structured results
   - Good for: When you need specific data from a tool
   - Returns: Structured response with capability, tool, parameters, and result

2. **`chat`**: Provides a more conversational experience with Claude
   - Good for: Natural back-and-forth conversations
   - Returns: Claude's natural language response
   - Maintains: Conversation history for context

Choose the method that best fits your use case. 