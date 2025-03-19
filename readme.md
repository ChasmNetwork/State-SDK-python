# State of Mika SDK

## Overview

State of Mika SDK (SoM) is a comprehensive framework that connects large language models (LLMs) with specialized capability servers using the Model Context Protocol (MCP). This integration enables AI systems to access a wide range of tools and services through a standardized interface.

Key benefits include:

- Seamless connection between LLMs and external capabilities
- Standardized communication through the Model Context Protocol
- Dynamic discovery and installation of capability servers
- Intelligent error handling with actionable suggestions
- Simplified integration of new capabilities into AI workflows

## Installation

Install the State of Mika SDK via pip:

```bash
pip install state_of_mika
```

Or from the source code:

```bash
git clone https://github.com/yourusername/StateOfMika-SDK.git
cd StateOfMika-SDK
pip install -e .
```

## Core Features

- **Capability Connection**: Connect LLMs to MCP capability servers with standardized interfaces
- **Server Discovery & Management**: Automatically find, install, and manage the appropriate servers for requested capabilities
- **Request Analysis**: Analyze natural language requests to determine required capabilities using Claude's language understanding
- **Auto-Installation**: Install required servers on-demand when capabilities are requested
- **Comprehensive Registry**: Access a growing catalog of available MCP servers and their capabilities
- **Intelligent Error Handling**: Receive detailed error analysis with human-readable suggestions for resolution
- **Environment Variable Management**: Configure API keys and other settings securely through environment variables
- **Context Management**: Properly manage server connections and resources throughout the application lifecycle
- **CLI Tools**: Command-line utilities for server management and capability execution

## API Access Requirements

**Important**: This SDK requires an Anthropic API key to function properly, as it uses Claude for request analysis. You can set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
# Or alternatively:
export MIKA_API_KEY="your_anthropic_api_key_here"
```

Some MCP servers may require additional API keys depending on the services they integrate with. For example, the weather capability requires:

```bash
export ACCUWEATHER_API_KEY="your_accuweather_api_key_here"
```

## How It Works

The State of Mika SDK provides a bridge between natural language requests and specialized capability servers:

1. A natural language request is received from the user or an LLM
2. Claude analyzes the request to determine the required capability and parameters
3. The SDK locates the appropriate MCP server for that capability
4. If needed, the server is automatically installed
5. The SDK connects to the server and executes the requested operation
6. Results or helpful error information are returned to the calling application

## Usage Examples

### High-Level Interface with SoMAgent

```python
import asyncio
from state_of_mika import SoMAgent

async def process_request():
    # Initialize the agent with your API key (or set env var ANTHROPIC_API_KEY/MIKA_API_KEY)
    agent = SoMAgent(api_key="your_api_key_here", auto_install=True)
    await agent.setup()
    
    # Process a user request
    result = await agent.process_request("What's the weather like in Tokyo today?")
    
    # Handle the response
    if result.get("status") == "success":
        print("Success:", result.get("result"))
    else:
        print("Error:", result.get("error"))
        print("Suggestion:", result.get("suggestion"))
    
    await agent.aclose()

asyncio.run(process_request())
```

### Direct Capability Access

```python
import asyncio
from state_of_mika import Connector

async def execute_capability():
    connector = Connector(auto_install=True)
    await connector.setup()
    
    # Execute a specific capability with predefined parameters
    result = await connector.execute_capability(
        capability="weather",
        tool_name="get_hourly_weather",
        parameters={"location": "Tokyo"}
    )
    
    print(result)
    await connector.aclose()

asyncio.run(execute_capability())
```

### Context Manager Pattern

```python
async def with_context_manager():
    connector = Connector(auto_install=True)
    await connector.setup()
    
    async with connector.connect_session("weather") as (server_name, client):
        result = await client.call_tool("get_hourly_weather", {"location": "London"})
        print(f"Result from {server_name}:", result)

asyncio.run(with_context_manager())
```

## Error Handling

SoM provides comprehensive error interpretation. When a tool connection fails, it returns:

```json
{
  "error": "Error message details",
  "error_type": "ApiKeyMissing",
  "status": "error",
  "explanation": "The operation failed because the required API key is missing",
  "suggestion": "Set the ACCUWEATHER_API_KEY environment variable",
  "requires_user_action": true,
  "tool_name": "get_hourly_weather",
  "capability": "weather"
}
```

This structured error format helps developers and LLMs understand what went wrong and how to fix it.

## Auto-Installation Settings

SoM can automatically install MCP servers as needed. You can enable this feature in two ways:

1. Set an environment variable:
   ```bash
   export AUTO_INSTALL_SERVERS="true"
   ```

2. Specify it directly in code:
   ```python
   connector = Connector(auto_install=True)
   # or
   agent = SoMAgent(auto_install=True)
   ```

## Command Line Interface (CLI)

SoM provides a command-line interface for managing servers and executing capabilities:

### View Available Servers

```bash
som list-servers
```

### Search for Servers by Capability

```bash
som search weather
```

### Install a Server

```bash
som install mcp_weather
```

### Execute a Capability

```bash
som execute weather get_hourly_weather --params '{"location": "Tokyo"}'
```

### Check if a Server is Installed

```bash
som check mcp_weather
```

### Update the Registry

```bash
som update-registry
```

### Interactive Mode

```bash
som interactive
```

This launches an interactive shell where you can test capabilities directly.

## Environment Variables

- `ANTHROPIC_API_KEY` or `MIKA_API_KEY`: Required for Claude analysis
- `AUTO_INSTALL_SERVERS`: Set to "true" to automatically install needed servers
- `USE_MOCK_DATA`: Set to "true" to use mock data instead of real server calls (for testing)
- `SOM_LOCAL_DEV`: Set to "true" to prioritize locally installed servers over registry versions
- Server-specific API keys (as required by individual servers)

## Adding Custom MCP Servers

### 1. Adding to Local Registry

You can add custom MCP servers to your local registry in two ways:

#### Using the CLI:

```bash
som add-server --name "my_custom_server" --description "My custom MCP server" --capabilities "custom,tools" --install-type "pip" --package "my-custom-package"
```

#### Editing the Registry File Directly:

The registry is stored in `~/.som/registry.json` or in the package's registry directory. You can add a new server entry:

```json
{
  "name": "mcp_custom",
  "description": "My custom MCP server",
  "categories": ["custom"],
  "capabilities": ["custom_capability"],
  "version": "0.1.0",
  "install": {
    "type": "pip",
    "repository": "https://github.com/yourusername/your-repo.git",
    "package": "mcp-custom-package",
    "global": true
  }
}
```

### 2. Installing Custom Packages Not in Registry

You can install any MCP-compatible package directly:

```bash
# Install from PyPI
pip install mcp-custom-package

# Install from GitHub
pip install git+https://github.com/yourusername/your-repo.git

# Then register it with SoM
som add-server --name "mcp_custom" --description "Custom server" --capabilities "custom" --install-type "already-installed"
```

### 3. Creating Your Own MCP Server

To create your own MCP server:

1. Start with the MCP template: https://github.com/outlines-dev/mcp-server-template
2. Implement your server's functionality
3. Install your package: `pip install -e .`
4. Register it with SoM using the CLI

## Advanced Configuration

### Custom Registry Location

```python
from pathlib import Path
from state_of_mika import Registry, Connector

registry = Registry(registry_file=Path("/path/to/custom/registry.json"))
connector = Connector(registry=registry)
```

### Semantic Search in the Registry

```python
from state_of_mika import Registry

registry = Registry()
# Enhanced search with multiple criteria
servers = registry.enhanced_search(
    query="Find weather information", 
    categories=["weather"], 
    capabilities=["forecast"],
    include_score=True
)
```

## Available Capabilities

The SDK provides access to a growing ecosystem of capabilities, including:

- **Weather Information**: Current conditions, forecasts, and historical data
- **Web Search**: Query search engines and retrieve results
- **Time and Date**: Time zones, conversions, and scheduling
- **File Operations**: Reading, writing, and managing files
- **Web Browsing**: Automated browser interactions
- **Code Execution**: Run code in various languages
- **Data Analysis**: Process and analyze structured data
- **API Integration**: Connect to external API services
- **Database Access**: Query and manage databases
- **Media Processing**: Image, audio, and video operations

## Model Context Protocol (MCP)

The Model Context Protocol provides a standardized way for language models to communicate with capability servers. By using MCP, State of Mika SDK enables:

- Consistent interfaces across different capabilities
- Structured parameter passing and validation
- Standardized error handling
- Dynamic discovery of available tools
- Clear documentation of capabilities

## Troubleshooting

Common issues and solutions:

### API Key Issues

If you encounter errors about missing API keys:

```
Error: Authentication failed. API key is missing.
```

Make sure you've set the required environment variables.

### Server Installation Failures

If a server fails to install:

```
Error: Failed to install server for capability: weather
```

Try manually installing with pip and check for dependency conflicts.

### Connection Errors

If you see connection errors:

```
Error: Failed to connect to any server for capability: weather
```

Check your internet connection and server status.

## Development and Testing

For development, install the package with development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

Please include tests for new functionality.

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For additional help or to report issues:
- GitHub Issues: [Report an issue](https://github.com/stateofmika/som-sdk/issues)
- Documentation: [Full documentation](https://docs.stateofmika.dev) 