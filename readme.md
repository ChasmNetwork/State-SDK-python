# State of Mika SDK

The State of Mika SDK is a powerful connector that bridges large language models (LLMs) with capability servers using the Message-based Communication Protocol (MCP).

## Installation

You can install the State of Mika SDK directly from PyPI:

```bash
pip install state_of_mika
```

Or from the source code:

```bash
git clone https://github.com/yourusername/StateOfMika-SDK.git
cd StateOfMika-SDK
pip install -e .
```

## Features

- Connect LLMs to MCP capability servers
- Automatic server discovery and installation
- Support for various capabilities (weather, time, search, etc.)
- Environment variable configuration for secure API key management
- **NEW**: Dynamic tool discovery with Mika integration
- **NEW**: Intelligent error analysis and suggestion system

## Usage

### Basic Usage

```python
import asyncio
from state_of_mika import Connector

async def main():
    # Initialize the connector
    connector = Connector()
    await connector.setup()
    
    # Execute a capability
    result = await connector.execute_capability(
        capability="weather", 
        tool_name="get_weather", 
        parameters={"location": "Paris"}
    )
    
    print(f"Weather result: {result}")
    
    # Clean up
    await connector.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Mika for Tool Selection

```python
import asyncio
from state_of_mika import SoMAgent

async def main():
    # Initialize the agent with Mika integration
    agent = SoMAgent(auto_install=True)
    await agent.setup()
    
    # Process a natural language request
    result = await agent.process_request("What's the weather like in Paris today?")
    
    if result["status"] == "success":
        print(f"Weather data: {result['result']}")
    else:
        print(f"Error: {result['error']}")
        print(f"Suggestion: {result['suggestion']}")
    
    # Clean up
    await agent.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

### Weather capability

To use the weather capability, you need to set the AccuWeather API key:

```bash
export ACCUWEATHER_API_KEY="your_api_key_here"
```

You can get an API key from [AccuWeather Developer Portal](https://developer.accuweather.com/).

### Mika Integration

To use the Mika integration for automatic tool selection and error analysis, set your Mika API key:

```bash
export MIKA_API_KEY="your_api_key_here"
```

You can get an API key from [Mika Console](https://console.mika.io/).

## Dynamic Tool Discovery

The State of Mika SDK now includes a dynamic tool discovery system that:

1. Analyzes user requests using Mika to determine the required capability
2. Examines the registry of available servers and tools
3. Intelligently selects the most appropriate tool based on the server configurations
4. Returns detailed error analysis and suggestions when issues occur

This approach enables:
- Adding new tools without code changes
- Automatic adaptation to available tools and capabilities
- Helpful suggestions when requested capabilities aren't available

For detailed technical documentation on how this system works, see [Dynamic Tool Discovery](docs/dynamic-tool-discovery.md).

## Command Line Interface

The SDK also provides a command-line interface:

```bash
# Install a server
som-cli install mcp_weather

# List available servers
som-cli list
```

## Development

For development, install the package with development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## License

MIT License 