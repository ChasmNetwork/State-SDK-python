import asyncio
import logging
from state_of_mika.installer import Installer
from state_of_mika.registry import Registry

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test")

async def test_wolfram_installation():
    print("Testing Wolfram Alpha installation...")
    
    # Create Registry and Installer
    registry = Registry()
    installer = Installer(registry)
    
    # Get the Wolfram Alpha server from the registry
    server = registry.get_server_by_name('mcp_wolfram_alpha')
    
    # Check if it's installed before
    is_installed_before = registry.is_server_installed('mcp_wolfram_alpha')
    print(f"Is Wolfram Alpha installed before: {is_installed_before}")
    
    if not is_installed_before:
        print("Installing Wolfram Alpha...")
        success = await installer.install_server(server)
        print(f"Installation success: {success}")
        
        # Check if it's installed after
        is_installed_after = registry.is_server_installed('mcp_wolfram_alpha')
        print(f"Is Wolfram Alpha installed after: {is_installed_after}")
    else:
        print("Wolfram Alpha is already installed.")

if __name__ == "__main__":
    asyncio.run(test_wolfram_installation()) 