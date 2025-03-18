"""
Example of using State of Mika with LangChain.

This example shows how to connect a LangChain agent to MCP servers.
This is a simple starter example - see the README for more advanced usage patterns.
"""

import asyncio
import os
from typing import List, Dict

from langchain.llms import OpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import BaseTool

from state_of_mika import Mika

async def main():
    """Run the example."""
    print("Starting LangChain + MCP example...")
    
    try:
        # Initialize OpenAI API key (replace with your actual key)
        # IMPORTANT: Replace this with your actual OpenAI API key
        os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY"
        
        # For Brave Search, you would also need to set:
        # os.environ["BRAVE_SEARCH_API_KEY"] = "YOUR_BRAVE_KEY"
        
        # Create a LangChain LLM
        llm = OpenAI(temperature=0)
        
        # Create a standard LangChain agent
        # Start with some basic tools
        tools = []
        
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        
        # Initialize Mika
        mika = Mika()
        
        # Connect to MCP servers
        print("Connecting to MCP servers...")
        await mika.connect(agent, servers=["brave_search", "filesystem"])
        
        print("Connection established! The agent now has MCP capabilities.")
        
        # Run a search using the agent
        result = await agent.arun(
            "Search for information about the Model Context Protocol (MCP)"
        )
        
        print("\nSearch result:")
        print(result)
        
        # Use filesystem tools
        result = await agent.arun(
            "Create a new text file called 'mcp_info.txt' containing a brief description of MCP"
        )
        
        print("\nFile creation result:")
        print(result)
        
        # Read the file back
        result = await agent.arun(
            "Read the contents of 'mcp_info.txt'"
        )
        
        print("\nFile contents:")
        print(result)
        
    except Exception as e:
        print(f"\nError during example: {e}")
        if "API key" in str(e):
            print("Make sure to set your API keys before running this example.")
    
    finally:
        # Clean up
        print("\nDisconnecting from MCP...")
        if 'agent' in locals() and 'mika' in locals():
            await mika.disconnect(agent)
        
        print("Example completed!")

if __name__ == "__main__":
    asyncio.run(main())