# State of Mika SDK (SoM)

## Overview

State of Mika SDK (SoM) is an AI capability routing system that:

1. Analyzes natural language requests using Claude
2. Identifies required capabilities and tools
3. Locates, installs (if needed), and connects to appropriate capability servers
4. Returns structured responses or helpful error suggestions to your LLM agent

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
- `ClaudeAdapter`: Analyzes requests to determine required capabilities

## Error Handling

SoM provides intelligent error interpretation. When a tool connection fails, it returns:

```json
{
  "error": "Error message details",
  "status": "error",
  "suggestion": "Human-readable suggestion to fix the problem",
  "tool_name": "name_of_tool"
}
```

Your LLM can use this information to explain the issue to users and suggest solutions.

## Environment Variables

- `AUTO_INSTALL_SERVERS`: Set to "true" to automatically install needed servers

## Integration

Minimal integration example:

```python
import asyncio
from state_of_mika import Connector

async def process_user_query(query):
    connector = Connector()
    await connector.setup()
    
    # Claude determines capability and tool
    capability = "weather"  # (dynamically determined by SoM)
    tool_name = "get_weather"  # (dynamically determined by SoM)
    parameters = {"location": "Tokyo"}  # (dynamically determined by SoM)
    
    result = await connector.execute_capability(capability, tool_name, parameters)
    
    # Check for errors and process suggestions
    if isinstance(result, dict) and result.get("status") == "error":
        error_message = result.get("error", "Unknown error")
        suggestion = result.get("suggestion", "No suggestion available")
        
        # Your LLM can use this information to explain the issue to the user
        response = f"I encountered an issue: {error_message}. {suggestion}"
    else:
        # Process successful result
        response = f"Here's the information: {result}"
    
    await connector.aclose()
    return response
```

For more examples, see the project documentation. 