# MCP Integration in State of Mika SDK

This document explains how the State of Mika SDK integrates with the Model Context Protocol (MCP) ecosystem to connect Language Models (like Claude) with MCP servers.

## Overview

The Model Context Protocol (MCP) is an open protocol that enables LLMs to access external tools and data in a standardized way. The State of Mika SDK serves as a bridge between LLMs and MCP servers, handling:

1. Discovery of MCP servers based on capabilities
2. Installation of servers when needed
3. Connection management
4. Tool execution and response formatting

## Integration Architecture

```
┌─────────────┐         ┌───────────────┐         ┌─────────────┐
│             │         │               │         │             │
│    LLM      │ ◄─────► │  State of     │ ◄─────► │  MCP        │
│  (Claude)   │         │  Mika SDK     │         │  Servers    │
│             │         │               │         │             │
└─────────────┘         └───────────────┘         └─────────────┘
```

## Key Integration Components

### 1. Connector

The `Connector` class is the core of our MCP integration:

- Uses `AsyncExitStack` for proper lifecycle management of server connections
- Implements context managers for safe resource handling
- Handles server discovery, installation, and connection
- Provides clean interfaces for tool execution
- Manages multiple simultaneous connections to different servers

```python
# Example using the connector context manager
async with connector.connect_session("weather") as (server_name, client):
    result = await client.call_tool("get_weather", {"location": "Paris"})
```

### 2. Claude Adapter

The `ClaudeAdapter` provides a bridge between Claude and MCP servers:

- Interprets natural language requests to extract capabilities, tools and parameters
- Connects to appropriate MCP servers via the Connector
- Executes tools and formats responses
- Maintains conversation history
- Supports multimodal interactions with image processing

```python
# Example using the Claude adapter
adapter = ClaudeAdapter()
await adapter.setup()
response = await adapter.process_request("What's the weather in Paris?")
```

### 3. Registry

The `Registry` component manages information about available MCP servers:

- Maintains a database of server capabilities
- Provides search functionality to find servers by capability
- Tracks installation status of servers

### 4. Installer

The `Installer` component handles the installation of MCP servers:

- Supports different installation methods (pip, npm, etc.)
- Handles dependencies
- Manages server versioning

## MCP Client Usage

Our SDK leverages the official MCP Python SDK's client capabilities:

```python
# We use the MCP SDK's ClientSession for server interaction
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Create server parameters
server_params = StdioServerParameters(
    command="python",
    args=["-m", "server_name"],
    env={}
)

# Connect to server
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Use the session to interact with the server
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("tool_name", {"param": "value"})
```

## Multimodal Support

Our MCP integration includes support for multimodal interactions:

- Image processing capabilities
- Structured responses with mixed media types
- Support for returning images from tools

## Best Practices

When using our MCP integration:

1. **Resource Management**: Always use context managers or ensure proper cleanup with `disconnect_all()`
2. **Error Handling**: Implement appropriate try/except blocks around tool executions
3. **Capability Discovery**: Use capability-based server discovery rather than hardcoding server names
4. **Conversation History**: Leverage the chat history functionality for more coherent interactions

## Example Usage

Here's a complete example of using our MCP integration with Claude:

```python
from state_of_mika.adapters.claude import ClaudeAdapter

async def get_weather(location: str):
    # Create the adapter
    adapter = ClaudeAdapter()
    
    # Set up the adapter
    await adapter.setup()
    
    try:
        # Process a natural language request
        response = await adapter.process_request(f"What's the weather like in {location}?")
        
        if response["success"]:
            return response["result"]
        else:
            return f"Error: {response.get('error', 'Unknown error')}"
    finally:
        # Clean up resources
        await adapter.connector.disconnect_all()
```

## Future Enhancements

We continue to enhance our MCP integration with:

1. **Subscription Support**: Better handling of resource subscriptions
2. **Event Support**: Improved handling of MCP server events
3. **Prompts**: Support for MCP prompt capabilities
4. **Parallel Tool Execution**: Execute multiple tools simultaneously when appropriate 