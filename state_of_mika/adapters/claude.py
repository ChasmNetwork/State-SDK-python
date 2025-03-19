#!/usr/bin/env python
"""
Claude adapter module for State of Mika SDK

This module provides the ClaudeAdapter class for interpreting natural language
requests using Claude and executing the appropriate MCP tools.
"""

import os
import json
import base64
import logging
import asyncio
import importlib
from typing import Dict, List, Any, Optional, Union, Tuple

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    
logger = logging.getLogger(__name__)

class ClaudeAdapter:
    """
    Adapter for using Claude to interpret natural language requests
    
    This class handles:
    1. Processing natural language requests through Claude
    2. Extracting structured information about tools to execute
    3. Finding the appropriate server for the requested capability
    4. Executing the tool with the provided parameters
    5. Formatting the results for the user
    """
    
    def __init__(
        self, 
        model: str = "claude-3-sonnet-20240229", 
        connector: Optional["Connector"] = None,
        api_key: Optional[str] = None,
        testing_mode: bool = False
    ):
        """Initialize the Claude adapter.
        
        Args:
            model: The Claude model to use
            connector: The connector for MCP servers
            api_key: The Anthropic API key, if not provided will look for ANTHROPIC_API_KEY env var
            testing_mode: Whether to use testing mode without real API calls
        """
        # Initialize attributes
        self.model = model  # Make sure this is a string value
        self.api_key = api_key
        self.testing_mode = testing_mode
        self.client = None
        self.connector = connector
        self.conversation_history = []
        
        if not self.connector:
            # Import here to avoid circular imports
            from state_of_mika.connector import Connector
            self.connector = Connector()
        
    async def setup(self):
        """Set up the Claude adapter
        
        This method initializes the Claude client with the API key and
        creates a connector for MCP server interaction.
        
        Returns:
            None
            
        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set (in non-testing mode)
        """
        # For testing mode, we don't need a real API key
        if self.testing_mode:
            self.client = None
            logger.info("ClaudeAdapter initialized in testing mode")
            return
            
        # Check if we already have a client
        if self.client is not None:
            return
            
        # Check for API key in non-testing mode
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is required for ClaudeAdapter"
                )
                
        # Initialize the connector
        if not self.connector:
            # Import here to avoid circular imports
            from state_of_mika.connector import Connector
            self.connector = Connector()
            await self.connector.connect()
            
        # Check if Anthropic is available
        global HAS_ANTHROPIC
        if not HAS_ANTHROPIC:
            try:
                import anthropic
                HAS_ANTHROPIC = True
            except ImportError:
                logger.warning("Anthropic package not found. Using mock client.")
                from .mock import MockAnthropicClient
                self.client = MockAnthropicClient(api_key=self.api_key)
                return
            
        # Initialize the Claude client
        try:
            import anthropic
            logger.debug(f"Initializing Claude client with model: {self.model}")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Error initializing Claude client: {e}")
            raise
        
    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON from Claude's response
        
        Args:
            content: Text response from Claude
            
        Returns:
            Parsed JSON object
        """
        # Look for JSON code block
        json_start = content.find("```json")
        if json_start == -1:
            json_start = content.find("```")
            
        if json_start != -1:
            # Find the actual start of the JSON content
            json_start = content.find("{", json_start)
            
            # Find the end of the JSON content
            json_end = content.rfind("}")
            
            if json_start != -1 and json_end != -1:
                json_content = content[json_start:json_end + 1]
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON from Claude response: {e}")
                    
        # Fallback: try to find any JSON object in the response
        try:
            import re
            json_pattern = r'\{(?:[^{}]|(?R))*\}'
            matches = re.findall(json_pattern, content)
            if matches:
                return json.loads(matches[0])
        except Exception:
            pass
            
        logger.error(f"Could not extract JSON from Claude response: {content}")
        return {}
        
    async def reset_conversation(self):
        """Reset the conversation history."""
        logger.debug("Resetting conversation history")
        self.conversation_history = []
        
    async def process_request(self, request: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Process a request from the user.
        
        Args:
            request: The request from the user
            image_path: Optional path to an image for multimodal requests
            
        Returns:
            The response from Claude
        """
        try:
            logger.debug(f"Sending request to Claude: {request}")
            
            # For testing without the ANTHROPIC_API_KEY
            if self.testing_mode and not self.api_key:
                return {"success": False, "error": "Testing mode active but no API key provided. Unable to process request."}
                
            # Execute the tool
            return await self.execute_tool(request)
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {"success": False, "error": str(e)}

    async def chat(self, message: str, image_path: Optional[str] = None) -> str:
        """Chat with Claude and get a formatted response
        
        Args:
            message: The user message
            image_path: Optional path to an image for multimodal requests
            
        Returns:
            A formatted response string
        """
        result = await self.process_request(message, image_path)
        
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
            
        # Format the result for display
        result_data = result.get("result")
        
        if not result_data:
            return "No data returned from the request."
                
        # For regular execution
        capability = result.get("capability")
        data = result_data
        
        if capability == "weather":
            return f"The weather in {data.get('location', 'Unknown')} is {data.get('condition', 'unknown')} with a temperature of {data.get('temperature', 'unknown')}°C."
        elif capability == "search":
            results = data.get("results", [])
            response = "Here are the search results:\n\n"
            for i, res in enumerate(results, 1):
                response += f"{i}. {res.get('title', 'Unknown')}: {res.get('url', 'Unknown')}\n"
                response += f"   {res.get('snippet', 'No snippet available')}\n\n"
            return response
        else:
            # Generic formatting for other capabilities
            return f"Here's the {capability} information you requested:\n{json.dumps(data, indent=2)}"

    async def execute_tool(self, request: str) -> Dict[str, Any]:
        """Execute a tool based on the request.
        
        Args:
            request: The request to execute
            
        Returns:
            The response from the tool
        """
        structured_request = await self._structure_request(request)
        
        if structured_request is None:
            return {"success": False, "error": "Failed to structure request"}
            
        capability = structured_request.get('capability')
        tool_name = structured_request.get('tool_name')
        parameters = structured_request.get('parameters', {})
        
        if not capability or not tool_name:
            return {
                "success": False, 
                "error": f"Missing capability or tool_name in structured request: {structured_request}"
            }

        logger.debug(f"Structured request: {structured_request}")
        
        try:
            # Try to find a server for the requested capability
            server = await self.connector.find_server_for_capability(capability)
            
            if not server:
                logger.error(f"No server found for capability: {capability}")
                return {"success": False, "error": f"No server available for capability: {capability}"}
                
            result = await self.connector.execute_tool(server, tool_name, parameters)
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": request
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": f"The result for your request about {capability} is: {result}"
            })
            
            # Trim history to last 10 messages
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
                
            return {"success": True, "capability": capability, "result": result}
            
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return {"success": False, "error": f"Failed to execute {tool_name} for capability {capability}: {str(e)}"}

    async def _structure_request(self, request: str, image_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Send a request to Claude to extract structured information.
        
        This method sends the user request to Claude and asks it to extract
        the capability, tool name, and parameters needed to execute the request.
        
        Args:
            request: The natural language request from the user
            image_data: Optional image data for multimodal requests
            
        Returns:
            A dictionary with capability, tool_name, and parameters,
            or None if the request could not be structured
        """
        logger.debug(f"Structuring request with Claude: {request}")
        
        # For testing mode, provide specific error
        if self.testing_mode:
            logger.error("Testing mode is enabled but no structure generation is implemented")
            return None
        
        # Ensure the client is initialized
        if not self.client:
            await self.setup()
            
        # Check again in case setup failed
        if not self.client:
            logger.error("Claude client is not initialized")
            return None
        
        # Build the system prompt
        system_prompt = """
        You are an AI assistant that helps extract structured information from natural language requests.
        Your task is to identify the capability needed, the tool to use, and the parameters required.
        
        When a user makes a request, respond ONLY with a JSON object containing:
        1. capability: The primary capability needed (e.g., weather, search, time)
        2. tool_name: The specific tool to use (e.g., get_weather, search_web)
        3. parameters: A dictionary of parameters needed for the tool
        
        Known capabilities:
        - weather: For weather information
        - search: For web search
        - time: For time/date information
        - general: For general conversation
        
        Example:
        For "What's the weather like in Paris?", respond with:
        ```json
        {
          "capability": "weather",
          "tool_name": "weather_lookup",
          "parameters": {
            "location": "Paris"
          }
        }
        ```
        """
        
        # Build the messages to send to Claude
        messages = []
        
        # Add conversation history for context (last few messages)
        if self.conversation_history:
            # Only include the last 5 messages to keep context concise
            for message in self.conversation_history[-5:]:
                messages.append(message)
        
        # Add the current user request
        user_message = {"role": "user", "content": request}
        messages.append(user_message)
        
        try:
            # Send the request to Claude
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=messages,
                max_tokens=1000
            )
            
            # Extract content from the response
            if hasattr(response, 'content') and response.content:
                content = response.content[0].text
                
                # Extract JSON from the response
                structured_data = self._extract_json_from_response(content)
                
                logger.debug(f"Structured data from Claude: {structured_data}")
                return structured_data
            else:
                logger.error("No content in Claude response")
                return None
                
        except Exception as e:
            logger.error(f"Error communicating with Claude API: {e}")
            return None 