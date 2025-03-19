#!/usr/bin/env python
"""
Script to import MCP servers from mcp-servers.md to servers.json
"""

import re
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set file paths
SCRIPT_DIR = Path(__file__).parent
MD_FILE = SCRIPT_DIR / "state_of_mika" / "registry" / "mcp-servers.md"
JSON_FILE = SCRIPT_DIR / "state_of_mika" / "registry" / "servers.json"
OUTPUT_JSON_FILE = SCRIPT_DIR / "state_of_mika" / "registry" / "servers_new.json"

# Define language mappings
LANGUAGE_EMOJI_MAP = {
    "🐍": "python",
    "📇": "typescript",
    "🏎️": "go",
    "🦀": "rust",
    "#️⃣": "csharp",
    "☕": "java"
}

# Define scope mappings
SCOPE_EMOJI_MAP = {
    "☁️": "cloud",
    "🏠": "local"
}

# Define OS mappings
OS_EMOJI_MAP = {
    "🍎": "macos",
    "🪟": "windows"
}

def parse_section(content: str, section_name: str) -> List[str]:
    """Extract a specific section from the markdown content"""
    section_pattern = fr"###\s+.*?{section_name}.*?\n(.*?)(?=###|\Z)"
    match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)
    
    if not match:
        logging.warning(f"Section {section_name} not found in the content")
        return []
        
    section_content = match.group(1).strip()
    lines = section_content.split('\n')
    # Filter out lines that are not server entries (they should start with -)
    return [line for line in lines if line.strip().startswith('-')]

def extract_servers_from_markdown(md_content: str) -> List[Dict[str, Any]]:
    """Extract server information from markdown content"""
    
    servers = []
    
    # Get server categories that we're interested in
    categories = [
        "Browser Automation", 
        "Databases", 
        "File Systems", 
        "Search", 
        "Weather"
    ]
    
    # Gather all server entries
    server_entries = []
    for category in categories:
        entries = parse_section(md_content, category)
        for entry in entries:
            server_entries.append((entry, category))
            
    # Regular expression to capture server entries
    server_pattern = r'- \[(.*?)\]\((.*?)\)(.*?) - (.*)'
    
    # Process each server entry
    for entry, category in server_entries:
        match = re.match(server_pattern, entry)
        if not match:
            logging.warning(f"Failed to parse server entry: {entry}")
            continue
            
        name = match.group(1).strip()
        url = match.group(2).strip()
        attributes = match.group(3).strip()
        description = match.group(4).strip()
        
        # Skip entries that aren't actual servers
        if "awesome-mcp" in url or "framework" in name.lower() or "utility" in name.lower():
            continue
            
        # Extract GitHub repo from URL
        repo_parts = url.split('github.com/')
        repo = repo_parts[1] if len(repo_parts) > 1 else None
        
        # Extract capabilities from the description and category
        capabilities = extract_capabilities(description, category)
        
        # Extract attributes
        is_official = "🎖️" in attributes
        language = next((LANGUAGE_EMOJI_MAP[emoji] for emoji in LANGUAGE_EMOJI_MAP if emoji in attributes), None)
        scope = next((SCOPE_EMOJI_MAP[emoji] for emoji in SCOPE_EMOJI_MAP if emoji in attributes), None)
        os_type = next((OS_EMOJI_MAP[emoji] for emoji in OS_EMOJI_MAP if emoji in attributes), None)
        
        server_info = {
            "name": sanitize_name(name),
            "description": description,
            "capabilities": capabilities,
            "version": "0.1.0",  # Default version
            "repository": url,
            "is_official": is_official,
            "language": language,
            "scope": scope,
            "category": category,
        }
        
        if os_type:
            server_info["os"] = os_type
            
        # Add installation and launch info based on language
        if language:
            install_info = create_install_info(language, repo, name)
            if install_info:
                server_info["install"] = install_info
                
        servers.append(server_info)
        
    logging.info(f"Found {len(servers)} servers across {len(categories)} categories")
    
    # Sort servers with official ones first
    servers.sort(key=lambda x: (not x.get("is_official", False), x.get("name", "")))
    
    return servers

def sanitize_name(name: str) -> str:
    """Sanitize server name"""
    # Remove @username/ prefix if present
    if '/' in name:
        name = name.split('/')[-1]
    
    # Remove special characters and convert to snake_case
    name = name.lower()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s-]+', '_', name)
    
    # Ensure it starts with mcp_ if not already
    if not name.startswith('mcp_'):
        name = f"mcp_{name}"
        
    return name

def extract_capabilities(description: str, category: str) -> List[str]:
    """Extract capabilities from description and category"""
    # Add the category as a capability
    capabilities = []
    
    # Map categories to capability keywords
    category_map = {
        "Browser Automation": ["browser", "web", "automation"],
        "Databases": ["database", "query", "sql"],
        "File Systems": ["file", "filesystem", "storage"],
        "Search": ["search", "information", "retrieval"],
        "Weather": ["weather", "forecast", "temperature"]
    }
    
    # Add category-based capabilities
    if category in category_map:
        capabilities.extend(category_map[category])
    
    # Extract key words from description
    words = re.findall(r'\b\w+\b', description.lower())
    
    # Filter out common words
    common_words = {"the", "a", "an", "and", "or", "for", "with", "that", "this", "to", "in", "on", "at", "by", "from"}
    capabilities.extend([word for word in words if len(word) > 3 and word not in common_words and word not in capabilities])
    
    # Limit to top 5 most relevant capabilities
    return list(set(capabilities))[:5]

def create_install_info(language: str, repo: Optional[str], name: str) -> Dict[str, Any]:
    """Create installation information based on language"""
    if not repo:
        return None
        
    if language == "python":
        return {
            "type": "pip",
            "repository": f"git+https://github.com/{repo}.git",
            "package": f"git+https://github.com/{repo}.git",
            "global": True
        }
    elif language == "typescript" or language == "javascript":
        return {
            "type": "npm",
            "repository": f"https://github.com/{repo}.git",
            "package": sanitize_name(name),
            "global": True
        }
    elif language == "go":
        return {
            "type": "go",
            "repository": f"https://github.com/{repo}.git",
            "package": f"github.com/{repo}",
            "global": True
        }
    else:
        # Default generic installation
        return {
            "type": "git",
            "repository": f"https://github.com/{repo}.git",
            "global": True
        }

def main():
    # Check if files exist
    if not MD_FILE.exists():
        logging.error(f"Markdown file not found: {MD_FILE}")
        return
    
    # Read current servers.json if exists
    current_servers = []
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, 'r') as f:
                data = json.load(f)
                current_servers = data.get("servers", [])
                logging.info(f"Loaded {len(current_servers)} servers from existing servers.json")
        except Exception as e:
            logging.error(f"Error reading servers.json: {e}")
            
    # Read markdown file
    try:
        with open(MD_FILE, 'r', encoding='utf-8') as f:
            md_content = f.read()
            logging.info(f"Successfully read markdown file: {MD_FILE}")
    except Exception as e:
        logging.error(f"Error reading markdown file: {e}")
        return
        
    # Extract servers from markdown
    new_servers = extract_servers_from_markdown(md_content)
    logging.info(f"Extracted {len(new_servers)} servers from markdown")
    
    # Merge with existing servers, preferring existing configurations
    # Create a map of existing servers by name for quick lookup
    existing_servers_map = {server["name"]: server for server in current_servers}
    
    # For each new server, check if it exists and update accordingly
    merged_servers = []
    for new_server in new_servers:
        name = new_server["name"]
        if name in existing_servers_map:
            # Server exists, preserve its configuration but add any new metadata
            existing_server = existing_servers_map[name]
            if "language" not in existing_server and "language" in new_server:
                existing_server["language"] = new_server["language"]
            if "scope" not in existing_server and "scope" in new_server:
                existing_server["scope"] = new_server["scope"]
            if "is_official" not in existing_server and "is_official" in new_server:
                existing_server["is_official"] = new_server["is_official"]
            if "repository" not in existing_server and "repository" in new_server:
                existing_server["repository"] = new_server["repository"]
            merged_servers.append(existing_server)
        else:
            # New server, add it
            # Remove metadata fields that don't belong in the final output
            server_to_add = {k: v for k, v in new_server.items() 
                            if k not in ["is_official", "category"]}
            merged_servers.append(server_to_add)
    
    # Add existing servers that weren't in the new servers list
    for name, server in existing_servers_map.items():
        if name not in [s["name"] for s in merged_servers]:
            merged_servers.append(server)
    
    # Sort servers: official first, then alphabetically
    merged_servers.sort(key=lambda x: (not x.get("is_official", False), x.get("name", "")))
    
    # Remove temporary fields used for sorting
    for server in merged_servers:
        if "is_official" in server:
            del server["is_official"]
    
    # Create output data
    output_data = {"servers": merged_servers}
    
    # Write output to new file
    try:
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
            logging.info(f"Successfully wrote {len(merged_servers)} servers to {OUTPUT_JSON_FILE}")
    except Exception as e:
        logging.error(f"Error writing output file: {e}")
        return
        
    logging.info(f"Process completed successfully. Please review {OUTPUT_JSON_FILE} before replacing servers.json")
    
    # Generate a summary of changes
    added_servers = [s["name"] for s in merged_servers if s["name"] not in [existing["name"] for existing in current_servers]]
    updated_servers = [s["name"] for s in merged_servers if s["name"] in [existing["name"] for existing in current_servers] and s != existing_servers_map.get(s["name"])]
    
    if added_servers:
        logging.info(f"Added {len(added_servers)} new servers: {', '.join(added_servers)}")
    if updated_servers:
        logging.info(f"Updated {len(updated_servers)} existing servers: {', '.join(updated_servers)}")
    
if __name__ == "__main__":
    main() 