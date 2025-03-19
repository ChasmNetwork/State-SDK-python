"""
Enhanced Registry module for managing MCP servers.

This module provides improved functionality to:
1. Access the MCP server registry with efficient indexing
2. Search for servers based on capabilities, categories, and keywords
3. Support semantic search for natural language queries
4. Rank and score search results by relevance
5. Provide metadata about available servers
"""

import json
import logging
import os
import re
import aiohttp
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from difflib import SequenceMatcher
from collections import defaultdict

logger = logging.getLogger(__name__)

class Registry:
    """
    Enhanced Registry for MCP servers.
    
    Provides efficient access to the central registry of MCP servers and 
    allows searching for servers based on multiple criteria with advanced
    semantic matching capabilities.
    """
    
    def __init__(self, 
                registry_url: Optional[str] = None,
                registry_file: Optional[Path] = None,
                cache_dir: Optional[Path] = None,
                build_indexes: bool = True):
        """
        Initialize the Registry.
        
        Args:
            registry_url: URL for the remote registry (defaults to GitHub registry)
            registry_file: Path to local registry file (defaults to ~/.som/registry.json)
            cache_dir: Directory for caching registry (defaults to ~/.som)
            build_indexes: Whether to build search indexes on initialization
        """
        self.home_dir = Path.home() / '.som'
        self.cache_dir = cache_dir or self.home_dir
        
        # Use the local registry.json file in our package directory if no custom path is provided
        if registry_file is None:
            import importlib.resources
            package_dir = Path(__file__).parent
            self.registry_file = package_dir / 'registry' / 'servers.json'
        else:
            self.registry_file = registry_file
            
        self.registry_url = registry_url or "https://raw.githubusercontent.com/stateofmika/registry/main/servers.json"
        
        # Create necessary directories
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Dictionary to store server data
        self.servers: Dict[str, Dict[str, Any]] = {}
        
        # Advanced search indexes
        self.category_index: Dict[str, List[str]] = defaultdict(list)
        self.capability_index: Dict[str, List[str]] = defaultdict(list)
        self.keyword_index: Dict[str, List[str]] = defaultdict(list)
        self.description_tokens: Dict[str, List[str]] = {}
        self.official_servers: List[str] = []
        self.all_categories: Set[str] = set()
        self.all_capabilities: Set[str] = set()
        
        # Load the registry from local file
        self._load_registry()
        
        # Build the indexes if requested
        if build_indexes and self.servers:
            self._build_indexes()
    
    def _load_registry(self) -> None:
        """Load the registry from the local file or create a new one."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    
                # The new format might have server entries in different places
                # 1. Check for the new format with categorized sections
                if isinstance(data, dict):
                    # Extract servers array
                    servers_list = data.get('servers', [])
                    
                    # Also check if there are frameworks and utilities lists
                    for section in ['frameworks', 'utilities']:
                        if section in data:
                            # Add a section identifier to each item in these lists
                            for item in data[section]:
                                item['_section'] = section
                            servers_list.extend(data[section])
                            
                # 2. Check for the old format (just an array of servers)
                elif isinstance(data, list):
                    servers_list = data
                # 3. Finally, check for the old format with servers in a 'servers' property
                elif isinstance(data, dict) and 'servers' in data and isinstance(data['servers'], list):
                    servers_list = data['servers']
                else:
                    servers_list = []
                
                # Convert from list to dict with server name as key
                self.servers = {server['name']: server for server in servers_list if 'name' in server}
                
                logger.info(f"Loaded {len(self.servers)} servers from registry")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading registry: {e}")
                self.servers = {}
        else:
            logger.info("No local registry found")
            self.servers = {}
    
    def _build_indexes(self) -> None:
        """Build search indexes for fast lookups."""
        # Reset all indexes
        self.category_index = defaultdict(list)
        self.capability_index = defaultdict(list)
        self.keyword_index = defaultdict(list)
        self.description_tokens = {}
        self.official_servers = []
        self.all_categories = set()
        self.all_capabilities = set()
        
        # Build indexes from server data
        for server_name, server_data in self.servers.items():
            # Index by category
            categories = server_data.get('categories', [])
            if isinstance(categories, list):
                for category in categories:
                    self.category_index[category].append(server_name)
                    self.all_categories.add(category)
            
            # Index by capability
            capabilities = server_data.get('capabilities', [])
            if isinstance(capabilities, list):
                for capability in capabilities:
                    self.capability_index[capability].append(server_name)
                    self.all_capabilities.add(capability)
            
            # Index by keywords (if present)
            keywords = server_data.get('keywords', [])
            if isinstance(keywords, list):
                for keyword in keywords:
                    self.keyword_index[keyword].append(server_name)
            
            # Tokenize description for full-text search
            description = server_data.get('description', '')
            if description:
                # Simple tokenization: lowercase, split by non-alphanumeric chars, filter empty
                tokens = [token.lower() for token in re.split(r'\W+', description) if token]
                self.description_tokens[server_name] = tokens
            
            # Track official servers
            if server_data.get('official', False):
                self.official_servers.append(server_name)
        
        logger.info(f"Built search indexes: {len(self.category_index)} categories, "
                   f"{len(self.capability_index)} capabilities, "
                   f"{len(self.keyword_index)} keywords, "
                   f"{len(self.official_servers)} official servers")
    
    def _save_registry(self) -> None:
        """Save the registry to the local file."""
        try:
            # Convert dict back to list for saving
            servers_list = list(self.servers.values())
            
            # Categorize servers by type
            result = {
                'version': '1.0.0',
                'last_updated': '2025-03-19',  # This should be dynamically generated
                'categories': sorted(list(self.all_categories)),
                'capabilities': sorted(list(self.all_capabilities)),
                'servers': []
            }
            
            # Split into core sections
            frameworks = []
            utilities = []
            servers = []
            
            for server in servers_list:
                # Remove the _section marker if it exists
                section = server.pop('_section', None) if isinstance(server, dict) else None
                
                if section == 'frameworks':
                    frameworks.append(server)
                elif section == 'utilities':
                    utilities.append(server)
                else:
                    servers.append(server)
            
            # Add the sections to the result
            if frameworks:
                result['frameworks'] = frameworks
            if utilities:
                result['utilities'] = utilities
            
            result['servers'] = servers
            
            with open(self.registry_file, 'w') as f:
                json.dump(result, f, indent=2)
                
            logger.info(f"Saved {len(servers_list)} servers to registry")
        except IOError as e:
            logger.error(f"Error saving registry: {e}")
    
    async def update(self, force: bool = False) -> bool:
        """
        Update the registry from the remote source.
        
        Args:
            force: Force update even if the registry was recently updated
            
        Returns:
            True if the registry was updated, False otherwise
        """
        # If we already have servers and we're not forcing an update,
        # consider the registry to be up-to-date
        if self.servers and not force:
            return False
            
        # First try to load from local file
        self._load_registry()
        
        # If we have servers now, consider it updated
        if self.servers:
            # Make sure indexes are built
            self._build_indexes()
            return True
            
        # Otherwise, try to fetch from remote
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.registry_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle different formats as in _load_registry
                        servers_list = []
                        if isinstance(data, dict):
                            servers_list = data.get('servers', [])
                            for section in ['frameworks', 'utilities']:
                                if section in data:
                                    for item in data[section]:
                                        item['_section'] = section
                                    servers_list.extend(data[section])
                        elif isinstance(data, list):
                            servers_list = data
                            
                        # Convert from list to dict with server name as key
                        self.servers = {server['name']: server for server in servers_list if 'name' in server}
                        
                        # Build the indexes
                        self._build_indexes()
                        
                        # Save the updated registry
                        self._save_registry()
                        
                        logger.info(f"Updated registry with {len(self.servers)} servers")
                        return True
                    else:
                        logger.warning(f"Failed to update registry: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error updating registry: {e}")
            return False
    
    def get_all_servers(self) -> List[Dict[str, Any]]:
        """
        Get all servers in the registry.
        
        Returns:
            List of all servers
        """
        return list(self.servers.values())
    
    def get_installed_servers(self) -> List[Dict[str, Any]]:
        """
        Get all installed servers.
        
        Returns:
            List of installed servers
        """
        # For now, we'll just return all servers
        # In a real implementation, we'd check which ones are installed
        return self.get_all_servers()
        
    def is_server_installed(self, server_name: str) -> bool:
        """
        Check if a server is installed
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            True if the server is installed, False otherwise
        """
        if server_name not in self.servers:
            logger.warning(f"Server {server_name} not found in registry")
            return False
            
        server = self.servers[server_name]
        
        # Check if the server has installation information
        install_info = server.get("install") or server.get("installation", {})
        if not install_info:
            logger.warning(f"No installation information for server {server_name}")
            return False
            
        install_type = install_info.get("type")
        
        # For pip packages, check if the package is installed using pip list
        if install_type == "pip":
            package_name = install_info.get("package", "")
            
            # Extract package name from GitHub URL if necessary
            if "github.com" in package_name:
                # Try to extract the repo name from the URL
                try:
                    repo_parts = package_name.split("/")
                    # Extract just the repository name without .git extension
                    pip_package_name = repo_parts[-1].replace(".git", "")
                    logger.debug(f"Extracted pip package name from GitHub URL: {pip_package_name}")
                except Exception as e:
                    logger.error(f"Error extracting package name: {e}")
                    pip_package_name = package_name
            else:
                pip_package_name = package_name
                
            # Special case for mcp_weather
            if server_name == "mcp_weather":
                pip_package_name = "mcp-weather"
                
            if not pip_package_name:
                logger.warning(f"Empty package name for server {server_name}")
                return False
            
            # Check if the package is in pip list
            try:
                logger.debug(f"Checking if {pip_package_name} is installed using pip list")
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "list"], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Error running pip list: {result.stderr}")
                    return False
                    
                # Check if the package name is in the output
                package_found = False
                for line in result.stdout.splitlines():
                    if pip_package_name.lower() in line.lower():
                        logger.debug(f"Package found in pip list: {line}")
                        package_found = True
                        break
                        
                if package_found:
                    logger.debug(f"Package {pip_package_name} is installed (pip list)")
                    return True
                else:
                    logger.debug(f"Package {pip_package_name} is not installed (pip list)")
                    return False
                    
            except Exception as e:
                logger.error(f"Error checking package installation with pip: {e}")
                
            # Fallback to the old import check method
            try:
                # Convert dash to underscore for importing
                import_name = pip_package_name.replace("-", "_")
                importlib = __import__("importlib")
                importlib.util.find_spec(import_name)
                logger.debug(f"Package {import_name} is installed (fallback to find_spec)")
                return True
            except (ImportError, ModuleNotFoundError, AttributeError):
                # Try to import directly
                try:
                    __import__(import_name)
                    logger.debug(f"Package {import_name} is installed (fallback to direct import)")
                    return True
                except:
                    logger.debug(f"Package {import_name} is not installed")
                    return False
                
        # For npm packages, check if the package is installed with npm list
        elif install_type == "npm":
            return False  # Not supported yet
        
        return False
    
    def search_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Search for servers supporting a specific capability
        
        Args:
            capability: The capability to search for
            
        Returns:
            List of server dictionaries that support the capability
        """
        if not self.servers:
            logger.warning("Registry is empty, cannot search for capability")
            return []
            
        # If indexes are not built, build them now
        if not self.capability_index:
            self._build_indexes()
            
        # Check for exact match in capability index
        matching_server_names = self.capability_index.get(capability, [])
        
        # If no exact match, try fuzzy matching
        if not matching_server_names:
            matching_server_names = self._fuzzy_match_capability(capability)
            
        # Convert server names to full server data
        matching_servers = []
        for server_name in matching_server_names:
            if server_name in self.servers:
                server_info = self.servers[server_name].copy()
                if "name" not in server_info:
                    server_info["name"] = server_name
                matching_servers.append(server_info)
                
        return matching_servers
    
    def _fuzzy_match_capability(self, capability: str, threshold: float = 0.7) -> List[str]:
        """
        Find capabilities that fuzzy match the given capability
        
        Args:
            capability: The capability to search for
            threshold: Minimum similarity score (0-1) to consider a match
            
        Returns:
            List of server names that have similar capabilities
        """
        matching_server_names = set()
        
        # Try to match against all capability names
        for existing_capability, server_names in self.capability_index.items():
            # Skip exact matches as they would have been caught already
            if existing_capability == capability:
                continue
                
            # Calculate similarity score
            similarity = SequenceMatcher(None, capability.lower(), existing_capability.lower()).ratio()
            
            # If similar enough, add the servers
            if similarity >= threshold:
                matching_server_names.update(server_names)
                
        return list(matching_server_names)
    
    def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Search for servers in a specific category
        
        Args:
            category: The category to search for
            
        Returns:
            List of server dictionaries in the category
        """
        if not self.servers:
            logger.warning("Registry is empty, cannot search by category")
            return []
            
        # If indexes are not built, build them now
        if not self.category_index:
            self._build_indexes()
            
        # Check for exact match in category index
        matching_server_names = self.category_index.get(category, [])
        
        # If no exact match, try fuzzy matching
        if not matching_server_names:
            # Get categories that are similar to the requested one
            similar_categories = self._fuzzy_match_text(category, self.all_categories)
            
            # Get servers for each similar category
            for similar_category in similar_categories:
                matching_server_names.extend(self.category_index.get(similar_category, []))
                
        # Convert server names to full server data
        matching_servers = []
        for server_name in matching_server_names:
            if server_name in self.servers:
                server_info = self.servers[server_name].copy()
                if "name" not in server_info:
                    server_info["name"] = server_name
                matching_servers.append(server_info)
                
        return matching_servers
    
    def _fuzzy_match_text(self, query: str, options: Set[str], 
                          threshold: float = 0.7, max_results: int = 5) -> List[str]:
        """
        Find texts that fuzzy match the query from a set of options
        
        Args:
            query: The text to search for
            options: Set of text options to match against
            threshold: Minimum similarity score (0-1) to consider a match
            max_results: Maximum number of results to return
            
        Returns:
            List of matching texts, sorted by similarity score
        """
        matches = []
        
        # Calculate similarity for all options
        for option in options:
            similarity = SequenceMatcher(None, query.lower(), option.lower()).ratio()
            if similarity >= threshold:
                matches.append((option, similarity))
                
        # Sort by similarity score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return the top matches
        return [match[0] for match in matches[:max_results]]
    
    def search_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for servers matching specific keywords
        
        Args:
            keywords: List of keywords to search for
            
        Returns:
            List of server dictionaries matching the keywords
        """
        if not self.servers:
            logger.warning("Registry is empty, cannot search by keywords")
            return []
            
        # If we don't have keyword indexes built, search descriptions instead
        if not self.keyword_index:
            return self.search_descriptions(keywords)
            
        matching_server_names = set()
        
        # For each keyword, add matching servers
        for keyword in keywords:
            # Check for exact matches
            server_names = self.keyword_index.get(keyword, [])
            matching_server_names.update(server_names)
            
            # Also check capability index for matches
            cap_server_names = self.capability_index.get(keyword, [])
            matching_server_names.update(cap_server_names)
            
            # Also search descriptions for this keyword
            desc_server_names = self._search_description_tokens(keyword)
            matching_server_names.update(desc_server_names)
            
        # Convert server names to full server data
        matching_servers = []
        for server_name in matching_server_names:
            if server_name in self.servers:
                server_info = self.servers[server_name].copy()
                if "name" not in server_info:
                    server_info["name"] = server_name
                matching_servers.append(server_info)
                
        return matching_servers
    
    def _search_description_tokens(self, token: str) -> List[str]:
        """
        Search tokenized descriptions for a specific token
        
        Args:
            token: Token to search for
            
        Returns:
            List of server names with matching descriptions
        """
        matching_server_names = []
        
        # Tokenizing the search term
        normalized_token = token.lower()
        
        # Check all tokenized descriptions
        for server_name, tokens in self.description_tokens.items():
            if normalized_token in tokens:
                matching_server_names.append(server_name)
                
        return matching_server_names
    
    def search_descriptions(self, terms: List[str]) -> List[Dict[str, Any]]:
        """
        Search descriptions for specific terms
        
        Args:
            terms: List of terms to search for in descriptions
            
        Returns:
            List of server dictionaries with matching descriptions
        """
        if not self.servers:
            logger.warning("Registry is empty, cannot search descriptions")
            return []
            
        # If description tokens aren't built, build them now
        if not self.description_tokens and self.servers:
            # Just build tokens for descriptions
            for server_name, server_data in self.servers.items():
                description = server_data.get('description', '')
                if description:
                    # Simple tokenization: lowercase, split by non-alphanumeric chars, filter empty
                    tokens = [token.lower() for token in re.split(r'\W+', description) if token]
                    self.description_tokens[server_name] = tokens
                    
        matching_server_names = set()
        
        # For each term, add matching servers
        for term in terms:
            server_names = self._search_description_tokens(term)
            matching_server_names.update(server_names)
            
        # Convert server names to full server data with scores
        matching_servers = []
        for server_name in matching_server_names:
            if server_name in self.servers:
                server_info = self.servers[server_name].copy()
                if "name" not in server_info:
                    server_info["name"] = server_name
                matching_servers.append(server_info)
                
        return matching_servers
    
    def get_official_servers(self) -> List[Dict[str, Any]]:
        """
        Get all official servers in the registry
        
        Returns:
            List of official server dictionaries
        """
        # If indexes are not built, build them now
        if not self.official_servers and self.servers:
            self._build_indexes()
            
        # Return the official servers
        return [self.servers[name] for name in self.official_servers if name in self.servers]
    
    def enhanced_search(self, 
                       query: str,
                       categories: Optional[List[str]] = None,
                       capabilities: Optional[List[str]] = None,
                       keywords: Optional[List[str]] = None,
                       include_score: bool = True,
                       max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced search combining multiple criteria with scoring
        
        This is the recommended search method for LLMs as it combines multiple
        search strategies and provides relevance scoring.
        
        Args:
            query: Natural language query to search for
            categories: Optional list of categories to filter by
            capabilities: Optional list of capabilities to filter by
            keywords: Optional list of additional keywords to consider
            include_score: Whether to include relevance score in results
            max_results: Maximum number of results to return
            
        Returns:
            List of matching servers with relevance scores
        """
        if not self.servers:
            logger.warning("Registry is empty, cannot perform enhanced search")
            return []
            
        # Make sure indexes are built
        if not self.capability_index:
            self._build_indexes()
            
        # Start with all servers
        candidate_servers = set(self.servers.keys())
        
        # If categories specified, filter by category
        if categories:
            category_servers = set()
            for category in categories:
                category_servers.update(self.category_index.get(category, []))
                
            # If we have category matches, filter candidates
            if category_servers:
                candidate_servers = candidate_servers.intersection(category_servers)
                
        # If capabilities specified, filter by capability
        if capabilities:
            capability_servers = set()
            for capability in capabilities:
                capability_servers.update(self.capability_index.get(capability, []))
                
            # If we have capability matches, filter candidates
            if capability_servers:
                candidate_servers = candidate_servers.intersection(capability_servers)
                
        # If no candidates at this point, try fuzzy matching
        if not candidate_servers and (categories or capabilities):
            # Try fuzzy matching on categories
            if categories:
                for category in categories:
                    similar_categories = self._fuzzy_match_text(category, self.all_categories)
                    for similar_category in similar_categories:
                        candidate_servers.update(self.category_index.get(similar_category, []))
                        
            # Try fuzzy matching on capabilities
            if capabilities and not candidate_servers:
                for capability in capabilities:
                    similar_capabilities = self._fuzzy_match_text(capability, self.all_capabilities)
                    for similar_capability in similar_capabilities:
                        candidate_servers.update(self.capability_index.get(similar_capability, []))
                        
        # If still no candidates, use all servers
        if not candidate_servers:
            candidate_servers = set(self.servers.keys())
            
        # Parse query into search terms
        search_terms = [term.lower() for term in re.split(r'\W+', query) if term and len(term) > 2]
        
        # Add specified keywords
        if keywords:
            search_terms.extend([kw.lower() for kw in keywords])
            
        # Compute scores for all candidates
        scored_results = []
        for server_name in candidate_servers:
            score = self._compute_server_score(server_name, search_terms, 
                                              categories=categories, 
                                              capabilities=capabilities)
            
            # Only include servers with non-zero scores
            if score > 0:
                result = self.servers[server_name].copy()
                if include_score:
                    result["_score"] = score
                scored_results.append((result, score))
                
        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results without score tuples
        return [result for result, _ in scored_results[:max_results]]
    
    def _compute_server_score(self, 
                             server_name: str, 
                             search_terms: List[str],
                             categories: Optional[List[str]] = None,
                             capabilities: Optional[List[str]] = None) -> float:
        """
        Compute relevance score for a server based on search criteria
        
        Higher scores indicate better matches. The scoring algorithm considers:
        - Exact matches in capabilities (highest weight)
        - Exact matches in categories
        - Matches in description
        - Matches in server name
        - Official servers get a bonus
        
        Args:
            server_name: Name of the server to score
            search_terms: List of search terms from query
            categories: Optional list of categories to boost score for
            capabilities: Optional list of capabilities to boost score for
            
        Returns:
            Relevance score as a float (higher is more relevant)
        """
        if server_name not in self.servers:
            return 0.0
            
        server = self.servers[server_name]
        score = 0.0
        
        # Get server metadata
        server_capabilities = set(server.get('capabilities', []))
        server_categories = set(server.get('categories', []))
        server_description = server.get('description', '').lower()
        server_is_official = server.get('official', False)
        
        # Check for exact capability matches (highest weight)
        if capabilities:
            for capability in capabilities:
                if capability in server_capabilities:
                    score += 10.0  # High weight for capability matches
                else:
                    # Try fuzzy matching
                    max_similar = 0.0
                    for server_cap in server_capabilities:
                        similarity = SequenceMatcher(None, capability.lower(), 
                                                    server_cap.lower()).ratio()
                        max_similar = max(max_similar, similarity)
                    
                    # Add partial score based on similarity
                    score += 5.0 * max_similar
        
        # Check for category matches
        if categories:
            for category in categories:
                if category in server_categories:
                    score += 5.0  # Medium weight for category matches
                else:
                    # Try fuzzy matching
                    max_similar = 0.0
                    for server_cat in server_categories:
                        similarity = SequenceMatcher(None, category.lower(), 
                                                    server_cat.lower()).ratio()
                        max_similar = max(max_similar, similarity)
                    
                    # Add partial score based on similarity
                    score += 2.5 * max_similar
        
        # Check for search terms in capabilities and description
        for term in search_terms:
            # Check server name (direct substring match)
            if term in server_name.lower():
                score += 2.0
            
            # Check if term exactly matches any capability
            for capability in server_capabilities:
                if term == capability.lower():
                    score += 3.0
                elif term in capability.lower():
                    score += 1.5
            
            # Check if term exactly matches any category
            for category in server_categories:
                if term == category.lower():
                    score += 2.0
                elif term in category.lower():
                    score += 1.0
            
            # Check if term is in the description (with position weighting)
            # Terms appearing earlier in description get higher weight
            if term in server_description:
                # Position bonus: earlier is better (higher score)
                position = server_description.find(term)
                position_factor = max(0, 1.0 - (position / 100.0))  # Decays with position
                score += 1.0 + (position_factor * 0.5)
                
                # Repetition bonus: more occurrences get a small bonus
                occurrences = server_description.count(term)
                if occurrences > 1:
                    score += 0.2 * min(5, occurrences - 1)  # Cap at 5 occurrences
        
        # Bonus for official servers
        if server_is_official:
            score += 2.0
            
        # Bonus for servers with examples or use_cases (shows it's well-documented)
        if 'examples' in server or 'use_cases' in server:
            score += 1.0
            
        return score
    
    def find_servers_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Alias for search_by_capability for backward compatibility.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of matching servers
        """
        logger.debug(f"Finding servers for capability: {capability}")
        return self.search_by_capability(capability)
    
    def get_server_by_name(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get server data by name.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server data or None if not found
        """
        return self.servers.get(server_name)
    
    def get_all_categories(self) -> List[str]:
        """
        Get all available categories in the registry.
        
        Returns:
            List of category names
        """
        # Build indexes if needed
        if not self.category_index and self.servers:
            self._build_indexes()
            
        return sorted(list(self.category_index.keys()))
    
    def get_all_capabilities(self) -> List[str]:
        """
        Get all available capabilities in the registry.
        
        Returns:
            List of capability names
        """
        # Build indexes if needed
        if not self.capability_index and self.servers:
            self._build_indexes()
            
        return sorted(list(self.capability_index.keys()))
    
    def get_server_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the registry contents.
        
        Returns:
            Dictionary with metadata
        """
        # Build indexes if needed
        if not self.capability_index and self.servers:
            self._build_indexes()
            
        # Gather metadata
        return {
            "server_count": len(self.servers),
            "official_count": len(self.official_servers),
            "categories": sorted(list(self.all_categories)),
            "capabilities": sorted(list(self.all_capabilities)),
            "category_counts": {k: len(v) for k, v in self.category_index.items()},
            "capability_counts": {k: len(v) for k, v in self.capability_index.items()},
        }
    
    async def get_server_suggestions(self, 
                                    query: str, 
                                    intent: Optional[str] = None,
                                    max_suggestions: int = 3) -> List[Dict[str, Any]]:
        """
        Get server suggestions based on a natural language query.
        
        This is a special method designed for LLMs to use when trying to 
        suggest appropriate servers for a user query.
        
        Args:
            query: Natural language query to find servers for
            intent: Optional intent classification to narrow down suggestions
                  (e.g., "database", "search", "file_operations")
            max_suggestions: Maximum number of servers to suggest
            
        Returns:
            List of suggested servers with relevance info
        """
        # Parse the query into categories, capabilities, and keywords
        categories = []
        capabilities = []
        keywords = []
        
        # Basic keyword extraction (could be improved with NLP)
        words = [w.lower() for w in re.split(r'\W+', query) if w and len(w) > 2]
        
        # Check if any word is a known category or capability
        for word in words:
            if word in self.all_categories:
                categories.append(word)
            if word in self.all_capabilities:
                capabilities.append(word)
            # Always keep as keyword too
            keywords.append(word)
            
        # If an intent is provided, use it as a category
        if intent and intent not in categories:
            categories.append(intent)
            
        # Perform enhanced search
        results = self.enhanced_search(
            query=query,
            categories=categories,
            capabilities=capabilities,
            keywords=keywords,
            include_score=True,
            max_results=max_suggestions
        )
        
        # Format results with suggestion context
        suggestions = []
        for result in results:
            # Extract score if present
            score = result.pop("_score", 0.0) if "_score" in result else 0.0
            
            suggestion = {
                "server": result,
                "relevance": "high" if score > 10 else "medium" if score > 5 else "low",
                "matched_categories": [c for c in categories if c in result.get("categories", [])],
                "matched_capabilities": [c for c in capabilities if c in result.get("capabilities", [])],
            }
            
            # Add reason if we can determine it
            reasons = []
            if suggestion["matched_categories"]:
                reasons.append(f"Matched categories: {', '.join(suggestion['matched_categories'])}")
            if suggestion["matched_capabilities"]:
                reasons.append(f"Matched capabilities: {', '.join(suggestion['matched_capabilities'])}")
            if result.get("official", False):
                reasons.append("This is an official server")
                
            if reasons:
                suggestion["reason"] = ". ".join(reasons)
                
            suggestions.append(suggestion)
            
        return suggestions