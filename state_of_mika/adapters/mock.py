"""
Mock adapters for testing without real API keys

This module contains mock implementations of various clients
that can be used for testing without requiring real API keys.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class MockContent:
    """Mock content object for the Anthropic API response."""
    def __init__(self, text):
        self.text = text
        self.type = "text"

class MockAnthropicClient:
    """Mock Anthropic client for testing without an API key."""
    
    def __init__(self, api_key=None):
        """Initialize the mock client."""
        self.api_key = api_key
        self.messages = MockMessages(self)
        logger.debug("Initialized MockAnthropicClient")
        
class MockMessage:
    """Mock message object for the Anthropic API response."""
    def __init__(self, content):
        self.content = content
        self.id = "msg_mock_id"
        self.model = "claude-mock"
        self.role = "assistant"
        self.type = "message"

class MockMessages:
    """Mock messages API for the Anthropic API."""
    
    def __init__(self, client):
        """Initialize the mock messages API."""
        self.client = client
        
    def create(self, model="claude-mock", messages=None, system=None, max_tokens=None):
        """Create a mock message response.
        
        Args:
            model: The model to use
            messages: The messages to send
            system: The system message
            max_tokens: The maximum number of tokens to generate
            
        Returns:
            A mock message response
        """
        logger.debug(f"MockMessages.create called with model: {model}")
        
        # Extract the user message
        user_message = None
        for message in messages:
            if message["role"] == "user":
                user_message = message["content"]
                break
                
        # Generate response based on the request
        if user_message and "weather" in user_message.lower():
            if "paris" in user_message.lower():
                location = "Paris"
            elif "london" in user_message.lower():
                location = "London"
            elif "tokyo" in user_message.lower():
                location = "Tokyo"
            else:
                location = "Unknown"
            
            # Create mock JSON response
            json_str = json.dumps({
                "capability": "weather",
                "tool_name": "weather_lookup",
                "parameters": {"location": location}
            }, indent=2)
            
        elif user_message and "time" in user_message.lower():
            # Extract location for time request
            if "tokyo" in user_message.lower():
                location = "Tokyo"
            elif "london" in user_message.lower():
                location = "London"
            elif "paris" in user_message.lower():
                location = "Paris"
            else:
                location = "Unknown"
                
            # Create mock JSON response
            json_str = json.dumps({
                "capability": "time",
                "tool_name": "get_time",
                "parameters": {"location": location}
            }, indent=2)
            
        elif user_message and ("search" in user_message.lower() or "find" in user_message.lower()):
            # Extract query
            query = user_message.lower().replace("search", "").replace("find", "").replace("for", "").strip()
            
            # Create mock JSON response
            json_str = json.dumps({
                "capability": "search",
                "tool_name": "search_web",
                "parameters": {"query": query}
            }, indent=2)
            
        else:
            # Default response
            json_str = json.dumps({
                "capability": "general",
                "tool_name": "respond",
                "parameters": {"query": user_message}
            }, indent=2)
            
        # Format the response inside a code block
        response_content = f"```json\n{json_str}\n```"
        
        # Create a mock content object
        mock_content = [MockContent(response_content)]
        
        # Create a mock message object
        return MockMessage(mock_content) 