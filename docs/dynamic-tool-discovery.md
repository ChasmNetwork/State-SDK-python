# Dynamic Tool Discovery with Mika Integration

The State of Mika SDK implements a flexible, intelligent system for discovering and utilizing tools based on user requests. This document explains the architecture and inner workings of this system.

## Architecture Overview

The dynamic tool discovery system consists of three main components:

1. **Mika Adapter**: Analyzes natural language requests to determine capabilities and tools
2. **Registry**: Maintains a catalog of available servers and their capabilities
3. **Connector**: Establishes connections to servers and executes tools

## How It Works

### 1. Request Analysis

When a user makes a natural language request (e.g., "What's the weather like in Paris?"), the `SoMAgent` passes this to the `MikaAdapter` for analysis:

```python
analysis = await self.mika_adapter.analyze_request(user_request)
```

The Mika API returns a structured response identifying:
- The capability required (e.g., "weather")
- A suggested tool name (e.g., "get_weather")
- Parameters needed (e.g., `{"location": "Paris"}`)

### 2. Tool Matching

Instead of relying on hardcoded mappings, the system dynamically matches the identified capability to available tools by:

1. Loading server configurations from the registry
2. Finding servers that support the requested capability
3. Matching the suggested tool name to actual tools in those servers

```python
def _find_matching_tool(self, capability, tool_name):
    # Find servers supporting this capability
    matching_servers = []
    for server in self.server_configs.get("servers", []):
        if capability in server.get("capabilities", []):
            matching_servers.append(server)
            
    # Find matching tools in these servers
    for server in matching_servers:
        schema = server.get("schema", {})
        
        # Check for exact matches, prefix matches, or related tools
        if tool_name in schema:
            return capability, tool_name
            
        get_capability = f"get_{capability}"
        if get_capability in schema:
            return capability, get_capability
            
        # Try other matching approaches...
```

### 3. Execution

Once the appropriate capability and tool are identified, the `SoMAgent` executes the tool:

```python
result = await self.connector.execute_capability(
    capability=capability,
    tool_name=tool_name,
    parameters=parameters
)
```

### 4. Error Analysis

If an error occurs, Mika analyzes it to provide helpful explanations and suggestions:

```python
error_analysis = await self.mika_adapter.analyze_error(
    error=result,
    original_request=user_request,
    context={
        "capability": capability,
        "tool_name": tool_name,
        "parameters": parameters
    }
)
```

## Benefits

This approach provides several key advantages:

### 1. Adaptability

The system adapts to whatever tools are available in the registry. As new servers and capabilities are added, the system automatically discovers and utilizes them without any code changes.

### 2. Resilience

If the exact tool isn't available, the system can find alternatives or provide helpful suggestions. For example, if a user asks for weather but the registry has a "forecast" tool instead, the system can adapt.

### 3. Developer Experience

Developers can focus on implementing tools without worrying about integration code. The system handles tool discovery, parameter mapping, and error handling automatically.

## Implementation Details

### Tool Matching Logic

The tool matching algorithm uses a hierarchical approach:

1. **Exact Match**: Look for a tool with exactly the suggested name
2. **Prefix Match**: Look for tools that start with "get_" followed by the capability
3. **Substring Match**: Look for tools that contain the capability name
4. **Fallback**: Suggest a logical tool name based on the capability

### Error Analysis

Mika analyzes errors with contextual understanding, providing:

- **Error Type**: Classification of the error (e.g., "API Key Missing")
- **Explanation**: User-friendly explanation of what went wrong
- **Suggestion**: Concrete steps to fix the issue
- **Action Required**: Whether user intervention is needed

## Example Flow

1. User request: "What's the weather like in Paris?"
2. Mika identifies: capability="weather", tool_name="get_weather"
3. System finds: Server "mcp_weather" with tool "get_hourly_weather"
4. System executes the tool with `{"location": "Paris"}`
5. Weather data is returned to the user

## Conclusion

The dynamic tool discovery system demonstrates how Mika can be used to bridge natural language requests with technical capabilities in a flexible, maintainable way. This approach allows the State of Mika SDK to grow organically as new capabilities are added, without requiring code changes for each new tool.

## Extending the System

### Adding New Capabilities

To add a new capability to the system, you only need to:

1. Create an MCP server that implements the capability
2. Add the server configuration to the registry
3. No code changes needed in the State of Mika SDK itself

For example, to add a new "translation" capability:

1. Create an MCP server implementing translation tools
2. Add its configuration to `servers.json`:

```json
{
  "name": "mcp_translation",
  "description": "MCP server for translating text between languages",
  "capabilities": ["translation", "language"],
  "version": "0.1.0",
  "install": {
    "type": "pip",
    "repository": "https://github.com/example/mcp-translation.git",
    "package": "mcp-translation",
    "global": true
  },
  "schema": {
    "translate_text": {
      "description": "Translate text from one language to another",
      "parameters": {
        "text": {
          "type": "string",
          "description": "The text to translate"
        },
        "source_language": {
          "type": "string",
          "description": "The source language code (e.g., 'en')"
        },
        "target_language": {
          "type": "string",
          "description": "The target language code (e.g., 'fr')"
        }
      }
    }
  }
}
```

3. That's it! The system will automatically discover and use this new capability.

### Custom Tool Matching Logic

If you need to implement custom tool matching logic, you can subclass the `MikaAdapter`:

```python
class MyCustomAdapter(MikaAdapter):
    def _find_matching_tool(self, capability, tool_name):
        # Your custom matching logic here
        # ...
        return capability, matched_tool_name
```

Then use your custom adapter with the `SoMAgent`:

```python
my_adapter = MyCustomAdapter()
agent = SoMAgent()
agent.mika_adapter = my_adapter
``` 