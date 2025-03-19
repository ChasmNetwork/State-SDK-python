"""
Claude Adapter module for analyzing requests and errors.

This module provides a layer between the IDE and tools, using Claude to:
1. Analyze requests to determine required capabilities and tools
2. Analyze errors to provide helpful explanations and suggestions
"""

import os
import json
import asyncio
import logging
import aiohttp
import ssl
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class ClaudeAdapter:
    """
    Adapter for Claude AI to analyze requests and interpret errors.
    
    This class serves as the deciding layer between the IDE and tools:
    - Analyzes user requests to determine required capabilities
    - Analyzes errors to provide helpful explanations and suggestions
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 model: str = "claude-3-sonnet-20240229",
                 max_tokens: int = 1024,
                 registry_path: str = "state_of_mika/registry/servers.json"):
        """
        Initialize the Claude Adapter.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum tokens for response
            registry_path: Path to the servers registry JSON file
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable.")
            
        self.model = model
        self.max_tokens = max_tokens
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.registry_path = registry_path
        self.server_configs = None
        
        # Create a custom SSL context that doesn't verify certificates
        # Note: This is NOT recommended for production use
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def load_server_configs(self):
        """Load server configurations from the registry."""
        if not os.path.exists(self.registry_path):
            logger.warning(f"Registry file not found at {self.registry_path}")
            self.server_configs = {"servers": []}
            return
            
        try:
            with open(self.registry_path, 'r') as f:
                self.server_configs = json.load(f)
                logger.info(f"Loaded {len(self.server_configs.get('servers', []))} server configurations")
        except Exception as e:
            logger.error(f"Error loading server configurations: {str(e)}")
            self.server_configs = {"servers": []}
            
    def _find_matching_tool(self, capability: str, tool_name: str) -> Tuple[str, str]:
        """
        Find the matching tool for the given capability and suggested tool name.
        
        This checks the server configurations to find:
        1. A server that supports the requested capability
        2. A tool in that server that matches or is similar to the suggested tool name
        
        Args:
            capability: The capability needed
            tool_name: The suggested tool name from Claude
            
        Returns:
            A tuple of (capability, tool_name) with the best matching tool
        """
        if not self.server_configs:
            logger.warning("Server configs not loaded, attempting to load now")
            asyncio.create_task(self.load_server_configs())
            return capability, tool_name
            
        # Find servers that support this capability
        matching_servers = []
        for server in self.server_configs.get("servers", []):
            if capability in server.get("capabilities", []):
                matching_servers.append(server)
                
        if not matching_servers:
            logger.warning(f"No servers found for capability: {capability}")
            return capability, tool_name
            
        # Find matching tools in these servers
        for server in matching_servers:
            # Check if the server has a schema section
            schema = server.get("schema", {})
            if not schema:
                continue
                
            # Check if the exact tool name exists
            if tool_name in schema:
                logger.info(f"Found exact tool match: {tool_name}")
                return capability, tool_name
                
            # Check for tools that start with "get_" + capability
            get_capability = f"get_{capability}"
            if get_capability in schema:
                logger.info(f"Found tool match via get_{capability}: {get_capability}")
                return capability, get_capability
                
            # If we still haven't found a match, look for any tool that has the capability in its name
            for available_tool in schema.keys():
                if capability.lower() in available_tool.lower():
                    logger.info(f"Found related tool: {available_tool}")
                    return capability, available_tool
                    
        # If we get here, no matching tool was found in any server
        # As a fallback, check if we can construct a reasonable tool name
        if not tool_name.startswith("get_"):
            suggested_tool = f"get_{capability}"
            logger.info(f"No matching tool found, suggesting: {suggested_tool}")
            return capability, suggested_tool
            
        return capability, tool_name
        
    async def analyze_request(self, user_request: str) -> Dict[str, Any]:
        """
        Analyze a user request to determine required capabilities and tools.
        
        Args:
            user_request: The natural language request from the user
            
        Returns:
            Dictionary with capability, tool_name, and parameters
        """
        # Ensure server configs are loaded
        if not self.server_configs:
            await self.load_server_configs()
            
        if not self.api_key:
            return {
                "error": "Missing Anthropic API key",
                "suggestion": "Set the ANTHROPIC_API_KEY environment variable"
            }
            
        # Create the system prompt for request analysis
        system_prompt = """
        You are an AI assistant that analyzes user requests to determine the appropriate capability and tool needed.
        Your task is to:
        1. Identify the capability (e.g., weather, search, file, etc.)
        2. Select the appropriate tool
        3. Extract necessary parameters
        
        Respond in JSON format only with these fields:
        {
            "capability": "string", // The main capability needed (e.g., "weather", "search")
            "tool_name": "string",  // The specific tool to use (e.g., "get_weather", "search_web")
            "parameters": {         // Parameters needed for the tool
                // key-value pairs
            }
        }
        """
        
        # Create the request for Claude
        request_data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_request}
            ]
        }
        
        # Send the request to Claude
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            async with session.post(
                self.api_url,
                headers={
                    "anthropic-version": "2023-06-01",
                    "x-api-key": self.api_key,
                    "content-type": "application/json"
                },
                json=request_data
            ) as response:
                # Check for errors
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error from Claude API: {error_text}")
                    return {
                        "error": f"Claude API error: {response.status}",
                        "suggestion": "Check API key and try again"
                    }
                
                # Parse the response
                response_data = await response.json()
                response_text = response_data.get("content", [{}])[0].get("text", "")
                
                # Try to parse the JSON response
                try:
                    # The response might have markdown code blocks, so extract just the JSON
                    json_text = response_text
                    if "```json" in response_text:
                        json_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        json_text = response_text.split("```")[1].split("```")[0].strip()
                        
                    result = json.loads(json_text)
                    
                    # Validate the required fields
                    if not result.get("capability"):
                        raise ValueError("Missing 'capability' in Claude response")
                    if not result.get("tool_name"):
                        raise ValueError("Missing 'tool_name' in Claude response")
                    if not isinstance(result.get("parameters"), dict):
                        raise ValueError("'parameters' must be a dictionary")
                        
                    # Find the best matching tool in the registry
                    capability, tool_name = self._find_matching_tool(
                        result["capability"],
                        result["tool_name"]
                    )
                    
                    # Update the result with the matched values
                    result["capability"] = capability
                    result["tool_name"] = tool_name
                        
                    return result
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing Claude response: {e}")
                    logger.debug(f"Claude response: {response_text}")
                    return {
                        "error": f"Failed to parse response from Claude: {str(e)}",
                        "suggestion": "The AI returned an invalid format. Try rephrasing your request."
                    }
    
    async def analyze_error(self, 
                           error: Union[str, Dict[str, Any]], 
                           original_request: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze an error to provide helpful explanations and suggestions.
        
        Args:
            error: Error message or dictionary with error details
            original_request: The original user request that caused the error
            context: Additional context about the error (capability, tool, etc.)
            
        Returns:
            Dictionary with error explanation and suggestions
        """
        if not self.api_key:
            return {
                "error": "Missing Anthropic API key",
                "suggestion": "Set the ANTHROPIC_API_KEY environment variable"
            }
            
        # Create the system prompt for error analysis
        system_prompt = """
        You are an AI assistant specializing in analyzing errors in tool execution.
        Your task is to:
        1. Analyze the error message
        2. Determine the root cause
        3. Provide a clear explanation
        4. Suggest concrete steps to fix the issue
        
        Respond in JSON format only with these fields:
        {
            "error_type": "string",         // Category of error (e.g., "API Key Missing", "Network Error")
            "explanation": "string",        // Clear explanation of what went wrong
            "suggestion": "string",         // Concrete steps to fix the issue
            "requires_user_action": boolean // Whether user needs to take action to fix it
        }
        """
        
        # Prepare error information
        if isinstance(error, dict):
            error_text = json.dumps(error, indent=2)
        else:
            error_text = str(error)
            
        # Prepare context information
        context_text = ""
        if context:
            context_text = f"\nError Context:\n{json.dumps(context, indent=2)}"
            
        # Prepare original request
        request_text = ""
        if original_request:
            request_text = f"\nOriginal Request: {original_request}"
            
        # Full prompt for Claude
        user_prompt = f"Error Message:\n{error_text}{context_text}{request_text}"
        
        # Create the request for Claude
        request_data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
        
        # Send the request to Claude
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            async with session.post(
                self.api_url,
                headers={
                    "anthropic-version": "2023-06-01",
                    "x-api-key": self.api_key,
                    "content-type": "application/json"
                },
                json=request_data
            ) as response:
                # Check for errors
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error from Claude API: {error_text}")
                    return {
                        "error": f"Claude API error: {response.status}",
                        "suggestion": "Check API key and try again"
                    }
                
                # Parse the response
                response_data = await response.json()
                response_text = response_data.get("content", [{}])[0].get("text", "")
                
                # Try to parse the JSON response
                try:
                    # The response might have markdown code blocks, so extract just the JSON
                    json_text = response_text
                    if "```json" in response_text:
                        json_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        json_text = response_text.split("```")[1].split("```")[0].strip()
                        
                    result = json.loads(json_text)
                    
                    # Add original error for reference
                    result["original_error"] = error
                    
                    return result
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing Claude response: {e}")
                    
                    # If we couldn't parse the JSON, try to at least extract the suggestion
                    suggestion = "Unable to parse Claude's analysis of this error."
                    if "suggestion" in response_text.lower():
                        suggestion_parts = response_text.lower().split("suggestion")
                        if len(suggestion_parts) > 1:
                            suggestion = suggestion_parts[1].split("\n")[0].strip(": ")
                    
                    return {
                        "error_type": "Parser Error",
                        "explanation": "Failed to parse Claude's analysis",
                        "suggestion": suggestion,
                        "requires_user_action": True,
                        "original_error": error
                    } 