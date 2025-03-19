# State of Mika SDK with Claude Integration

## Overview

The State of Mika SDK with Claude Integration provides a complete system where Claude AI acts as the "deciding layer" between your IDE/application and tool execution. This integration enables:

1. Smart request analysis - Claude determines what capabilities and tools are needed
2. Automatic tool selection, installation, and execution
3. Intelligent error analysis - Claude interprets errors and provides helpful explanations

## Architecture

```
IDE/Application
      ↓
  SoM Agent
      ↓
┌─────┴─────┐
│ Claude AI │ ← (Deciding Layer)
└─────┬─────┘
      ↓
┌─────┴─────┐
│ Connector │
└─────┬─────┘
      ↓
 Tool Servers
```

### Components

- **SoMAgent**: Main facade that integrates all components
- **ClaudeAdapter**: Interfaces with Claude AI for request and error analysis
- **Connector**: Manages connections to tool servers
- **Registry**: Stores information about available tool servers
- **Installer**: Handles installation of required servers

## How It Works

### Request Processing Flow

1. User sends a natural language request to SoMAgent
2. Claude analyzes the request to determine the required capability and tool
3. The Connector finds, installs (if needed), and connects to the appropriate server
4. The tool is executed and the result is returned
5. If any errors occur, Claude analyzes them and provides helpful explanations

### Error Handling Process

When an error occurs at any stage (analysis, connection, execution):

1. The error is captured and sent to Claude for analysis
2. Claude determines the error type, explanation, and suggested fix
3. A structured error response is returned to the IDE with:
   - Error message and type
   - Clear explanation in human-readable terms
   - Concrete suggestions for resolving the issue
   - Information on whether user action is required

## Usage

```python
import asyncio
from state_of_mika import SoMAgent

async def process_request():
    # Initialize the agent
    agent = SoMAgent(
        api_key="your_anthropic_api_key",  # Or use ANTHROPIC_API_KEY env var
        auto_install=True  # Automatically install tools when needed
    )
    
    # Set up the agent
    await agent.setup()
    
    try:
        # Process a user request
        result = await agent.process_request("What's the weather in Paris?")
        
        # Check if there was an error
        if result.get("status") == "error":
            print(f"Error: {result.get('error')}")
            print(f"Explanation: {result.get('explanation')}")
            print(f"Suggestion: {result.get('suggestion')}")
        else:
            print(f"Success! Result: {result.get('result')}")
            
    finally:
        # Clean up
        await agent.aclose()

# Run the function
asyncio.run(process_request())
```

## Error Response Structure

When an error occurs, the system returns a structured response with:

```json
{
  "status": "error",
  "error": "Original error message",
  "error_type": "Classification of the error (e.g., 'API Key Missing')",
  "explanation": "Human-readable explanation of what went wrong",
  "suggestion": "Concrete steps to fix the issue",
  "requires_user_action": true,
  "capability": "weather",
  "tool_name": "get_weather"
}
```

This information can be used by your application to:
- Display helpful error messages to users
- Automatically fix certain types of errors
- Provide guided troubleshooting

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude
- `AUTO_INSTALL_SERVERS`: Set to "true" to automatically install needed servers
- `ACCUWEATHER_API_KEY`: API key for weather capability (as an example)

### Custom Configuration

You can customize the SoMAgent behavior:

```python
agent = SoMAgent(
    api_key="your_anthropic_api_key",
    model="claude-3-opus-20240229",  # Use a different Claude model
    auto_install=False  # Disable automatic installation
)
```

## Example Error Scenarios

1. **Missing API Key**
   - Error: "API key required for AccuWeather"
   - Claude's Analysis: Identifies it as an API key issue
   - Suggestion: "Get an AccuWeather API key and set the ACCUWEATHER_API_KEY environment variable"

2. **Non-existent Capability**
   - Error: "No servers available for capability: math"
   - Claude's Analysis: Identifies it as a missing capability
   - Suggestion: "This SDK doesn't support math calculations. Consider using a different tool or library."

3. **Installation Failure**
   - Error: "Failed to install server: mcp_weather"
   - Claude's Analysis: Identifies installation issues
   - Suggestion: "Check your internet connection and try again. If the problem persists, try installing the package manually."

## Running the Test Script

A test script is provided to demonstrate the complete flow:

```bash
# Set your API keys
export ANTHROPIC_API_KEY=your_anthropic_api_key
export ACCUWEATHER_API_KEY=your_accuweather_api_key

# Run the test
python test_som_agent.py
``` 