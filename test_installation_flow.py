import asyncio
import logging
from state_of_mika.som_agent import SoMAgent

# Set up logging
logging.basicConfig(level=logging.DEBUG)

async def test_auto_installation():
    print("Testing auto-installation with a math problem...")
    
    # Create agent with auto_install enabled
    agent = SoMAgent(auto_install=True)
    
    # Set up the agent
    await agent.setup()
    
    # Process a request that requires Wolfram Alpha
    result = await agent.process_request('Solve this complex math equation: 3x^2 + 2x - 5 = 0')
    
    # Print the result
    print("\nRESULT:")
    print(result)
    
    # Clean up
    await agent.aclose()

# Run the test
if __name__ == "__main__":
    asyncio.run(test_auto_installation()) 