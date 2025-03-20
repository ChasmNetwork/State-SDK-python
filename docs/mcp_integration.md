# MCP Integration in State of Mika SDK

This document explains how the State of Mika SDK integrates with the Model Context Protocol (MCP) to provide a flexible and extensible framework for connecting large language models with capability servers.

## Overview

The Model Context Protocol (MCP) is a standardized protocol for communication between large language models (LLMs) and capability servers. It defines:

1. How LLMs and servers communicate
2. How capabilities and tools are discovered
3. How parameters are passed and validated
4. How results are returned

The State of Mika SDK provides a complete framework for:

- Discovering MCP servers for specific capabilities
- Managing server installations and dependencies
- Establishing connections with servers
- Executing tools with proper parameter handling
- Processing and validating results
- Providing structured error information when things go wrong

## Architecture

The SDK is built on a modular architecture with these key components:

```
SoMAgent
   ├── Registry (server discovery and metadata)
   ├── Installer (server installation)
   ├── Connector (server communication)
   └── MikaAdapter (request/error analysis)
```

Each component handles a specific part of the MCP integration process:

1. **Registry**: Maintains a catalog of available MCP servers and their capabilities
2. **Installer**: Handles the installation and updating of MCP servers
3. **Connector**: Manages connections to MCP servers and executes tools
4. **MikaAdapter**: Analyzes natural language requests and determines which capabilities are needed

## Natural Language to MCP Workflow

The MikaAdapter provides a bridge between Claude and MCP servers:

1. **Input**: User submits a natural language request (e.g., "What's the weather in Paris?")
2. **Analysis**: MikaAdapter analyzes the request to determine the required capability and parameters
3. **Server Discovery**: Registry identifies the appropriate server for the capability
4. **Connection**: Connector establishes a connection to the server
5. **Tool Execution**: Connector executes the appropriate tool with the extracted parameters
6. **Results**: Results are returned in a structured format for the calling application

## Dynamic Tool Discovery

MCP servers advertise their capabilities and available tools, allowing the SDK to dynamically discover and use them without prior knowledge.

The Registry maintains information about:

- Available servers by capability
- Installation methods for each server
- Schema information for tool parameters
- Version information and compatibility

## Example Usage

### Basic Example

```python
import asyncio
from state_of_mika import SoMAgent

async def main():
    # Initialize the agent
    agent = SoMAgent(auto_install=True)
    await agent.setup()
    
    try:
        # Process a natural language request
        result = await agent.process_request("What's the weather in Paris?")
        
        # Check if successful
        if result.get("status") == "success":
            print(f"Weather data: {result.get('result')}")
        else:
            print(f"Error: {result.get('error')}")
    finally:
        # Clean up resources
        await agent.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

### Direct Capability Access

```python
import asyncio
from state_of_mika import Connector

async def direct_capability():
    # Create a connector
    connector = Connector(auto_install=True)
    await connector.setup()
    
    try:
        # Execute a specific capability directly
        result = await connector.execute_capability(
            capability="weather",
            tool_name="get_hourly_weather",
            parameters={"location": "Paris"}
        )
        
        print("Weather data:", result)
    finally:
        # Clean up resources
        await connector.aclose()

if __name__ == "__main__":
    asyncio.run(direct_capability())
```

### Using the MikaAdapter for Request Analysis

When you need more control over the analysis process:

```python
import asyncio
from state_of_mika.mika_adapter import MikaAdapter
from state_of_mika import Connector

async def analyze_and_execute():
    # Create the adapter
    adapter = MikaAdapter()
    
    # Load server configurations
    await adapter.load_server_configs()
    
    # Create a connector
    connector = Connector(auto_install=True)
    await connector.setup()
    
    try:
        # Analyze the request
        request_analysis = await adapter.analyze_request(
            "What's the weather like in Tokyo today?"
        )
        
        # Extract information from the analysis
        capability = request_analysis.get("capability")
        tool_name = request_analysis.get("tool_name")
        parameters = request_analysis.get("parameters", {})
        
        print(f"Capability: {capability}")
        print(f"Tool: {tool_name}")
        print(f"Parameters: {parameters}")
        
        # Execute the capability
        result = await connector.execute_capability(
            capability=capability,
            tool_name=tool_name,
            parameters=parameters
        )
        
        print("Result:", result)
    finally:
        # Clean up
        await connector.aclose()

if __name__ == "__main__":
    asyncio.run(analyze_and_execute())
```

## Error Handling

The SDK provides comprehensive error handling with structured error information:

```python
try:
    result = await agent.process_request("What's the weather in Mars?")
    
    if result.get("status") != "success":
        error_type = result.get("error_type")
        suggestion = result.get("suggestion")
        
        print(f"Error type: {error_type}")
        print(f"Suggestion: {suggestion}")
        
        if result.get("requires_user_action"):
            print("This error requires user action to resolve.")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Advanced Use Cases

### Custom Error Analysis

```python
# Get an error from a failed operation
error_result = await connector.execute_capability(
    capability="weather",
    tool_name="get_hourly_weather",
    parameters={"location": "Invalid Location"}
)

# Use the MikaAdapter to analyze the error
error_analysis = await adapter.analyze_error(
    error=error_result,
    original_request="What's the weather in Invalid Location?",
    context={"capability": "weather"}
)

print(f"Error type: {error_analysis.get('error_type')}")
print(f"Explanation: {error_analysis.get('explanation')}")
print(f"Suggestion: {error_analysis.get('suggestion')}")
```

### Server Status Checking

```python
# Check if specific servers are installed and available
weather_status = await connector.check_server_status("weather")
search_status = await connector.check_server_status("search")

print(f"Weather server installed: {weather_status.get('installed')}")
print(f"Weather server available: {weather_status.get('available')}")
print(f"Search server installed: {search_status.get('installed')}")
print(f"Search server available: {search_status.get('available')}")
```

## Conclusion

The State of Mika SDK provides a comprehensive framework for integrating MCP servers with application code, handling the complexities of server discovery, installation, connection management, and error handling. 