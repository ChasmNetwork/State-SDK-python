"""
State of Mika Agent - Main interface for the IDE.

This module integrates the MikaAdapter with the Connector, Registry, and Installer
to provide a unified interface for the IDE.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union

from .registry import Registry
from .installer import Installer
from .connector import Connector
from .mika_adapter import MikaAdapter  # Updated import

logger = logging.getLogger(__name__)

class SoMAgent:
    """
    State of Mika Agent - Main interface for the IDE.
    
    This class integrates all components to provide a unified interface:
    - Uses Mika to analyze requests and determine capabilities
    - Finds, installs, and connects to the appropriate servers
    - Executes tools and returns structured responses
    - Analyzes errors and provides helpful suggestions
    """
    
    def __init__(self, 
                api_key: Optional[str] = None,
                model: str = "claude-3-sonnet-20240229",
                auto_install: bool = True):
        """
        Initialize the State of Mika Agent.
        
        Args:
            api_key: Mika API key (defaults to MIKA_API_KEY env var)
            model: Mika model to use
            auto_install: Whether to automatically install servers when needed
        """
        # Set up the environment
        if auto_install:
            os.environ["AUTO_INSTALL_SERVERS"] = "true"
        
        # Initialize components
        self.registry = Registry()
        self.installer = Installer(self.registry)
        self.connector = Connector(self.registry, self.installer)
        self.mika_adapter = MikaAdapter(api_key=api_key, model=model)
        
    async def setup(self):
        """Set up the agent by ensuring the registry is loaded."""
        await self.registry.update()
        await self.connector.setup()
        # Ensure Mika adapter has server configurations loaded
        await self.mika_adapter.load_server_configs()
        
    async def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Process a natural language request from the user.
        
        This is the main entry point for the IDE. It:
        1. Uses Mika to analyze the request
        2. Finds and connects to the appropriate server
        3. Executes the tool and returns the result
        4. Analyzes any errors that occur
        
        Args:
            user_request: Natural language request from the user
            
        Returns:
            Dictionary with the result or error information
        """
        logger.info(f"Processing user request: {user_request}")
        
        try:
            # Step 1: Analyze the request with Mika
            analysis = await self.mika_adapter.analyze_request(user_request)
            
            # Check for errors in the analysis
            if "error" in analysis:
                logger.error(f"Error analyzing request: {analysis['error']}")
                return {
                    "status": "error",
                    "error": analysis["error"],
                    "suggestion": analysis.get("suggestion", "Try rephrasing your request."),
                    "original_request": user_request
                }
                
            # Extract the capability, tool, and parameters
            capability = analysis["capability"]
            tool_name = analysis["tool_name"]
            parameters = analysis["parameters"]
            
            logger.info(f"Determined capability: {capability}, tool: {tool_name}")
            
            # Step 2: Execute the capability
            result = await self.connector.execute_capability(
                capability=capability,
                tool_name=tool_name,
                parameters=parameters
            )
            
            # Step 3: Check if the result is an error
            if isinstance(result, dict) and result.get("status") == "error":
                logger.warning(f"Error executing capability: {result.get('error')}")
                
                # Step 4: Analyze the error with Mika
                error_analysis = await self.mika_adapter.analyze_error(
                    error=result,
                    original_request=user_request,
                    context={
                        "capability": capability,
                        "tool_name": tool_name,
                        "parameters": parameters
                    }
                )
                
                # Combine the original error with Mika's analysis
                enhanced_error = {
                    "status": "error",
                    "error": result.get("error"),
                    "error_type": error_analysis.get("error_type"),
                    "explanation": error_analysis.get("explanation"),
                    "suggestion": error_analysis.get("suggestion"),
                    "requires_user_action": error_analysis.get("requires_user_action", True),
                    "original_request": user_request,
                    "capability": capability,
                    "tool_name": tool_name
                }
                
                return enhanced_error
            
            # Success case - return the result
            return {
                "status": "success",
                "result": result,
                "capability": capability,
                "tool_name": tool_name
            }
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            
            # Try to analyze the error with Mika
            try:
                error_analysis = await self.mika_adapter.analyze_error(
                    error=str(e),
                    original_request=user_request
                )
                
                return {
                    "status": "error",
                    "error": str(e),
                    "error_type": error_analysis.get("error_type", "Unexpected Error"),
                    "explanation": error_analysis.get("explanation", "An unexpected error occurred."),
                    "suggestion": error_analysis.get("suggestion", "Please try again or report this issue."),
                    "requires_user_action": error_analysis.get("requires_user_action", True),
                    "original_request": user_request
                }
            except:
                # If even Mika analysis fails, return a simple error
                return {
                    "status": "error",
                    "error": str(e),
                    "explanation": "An unexpected error occurred and could not be analyzed.",
                    "suggestion": "Please try again or report this issue.",
                    "original_request": user_request
                }
                
    async def aclose(self):
        """Close all connections and clean up resources."""
        await self.connector.aclose() 