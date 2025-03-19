# State of Mika SDK (SoM)

## Overview

State of Mika SDK (SoM) is an AI capability routing system that:

1. Analyzes natural language requests using Claude
2. Identifies required capabilities and tools
3. Locates, installs (if needed), and connects to appropriate capability servers
4. Returns structured responses or helpful error suggestions to your LLM agent

This system enables seamless integration of various capabilities (like weather data, search, file operations) into your AI applications without the need to manually code integrations for each service.

## Requirements

**Important**: This SDK requires an Anthropic API key to function properly, as it uses Claude for request analysis. You can set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
# Or alternatively:
export MIKA_API_KEY="your_anthropic_api_key_here"
```

You can obtain an API key by signing up at [Anthropic's website](https://www.anthropic.com/product).

Some MCP servers may require additional API keys depending on the services they integrate with. For example, the weather capability requires:

```bash
export ACCUWEATHER_API_KEY="your_accuweather_api_key_here"
```

## Installation

Install the State of Mika SDK via pip:

```bash
pip install state-of-mika
```

## How It Works

When integrated into an agent framework:

```
User Request → Your Agent → SoM SDK → Claude Analysis → Tool Selection → Tool Execution → Structured Response/Suggestions → Your Agent → User Response
```

### Example Flow

1. User asks: "What's the weather in Tokyo?"
2. Your agent passes this to SoM
3. SoM uses Claude to identify weather capability requirement
4. SoM checks if appropriate server is installed
   - If installed and working: connects and gets data
   - If missing or failing: provides human-readable error with suggestions

## Key Components

- `Connector`: Main interface for finding/connecting to capability servers
- `Registry`: Database of available capability servers
- `Installer`: Handles installation of required servers
- `MikaAdapter`: Analyzes requests to determine required capabilities

## Auto-Installation of Servers

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

## Usage Examples

### Using the SoMAgent (Recommended)

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

### Using the Connector Directly

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

SoM provides intelligent error interpretation. When a tool connection fails, it returns:

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

Your LLM can use this information to explain the issue to users and suggest solutions.

## Command Line Interface (CLI)

SoM provides a command-line interface for various operations:

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

### Local Development Mode

For developing and testing your own MCP servers:

```bash
export SOM_LOCAL_DEV=true
```

This will prioritize locally installed servers over registry versions.

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

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

Please include tests for new functionality.

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Developer Support

For additional help or to report issues:
- GitHub Issues: [Report an issue](https://github.com/stateofmika/som-sdk/issues)
- Documentation: [Full documentation](https://docs.stateofmika.dev) 