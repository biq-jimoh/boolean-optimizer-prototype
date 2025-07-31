"""
Brave Search Service for web searches
Handles statute and case law searches using the Brave Search API.
"""

import os
from typing import List, Dict, Optional
from brave import Brave, AsyncBrave
import asyncio


class BraveSearchService:
    """Service for performing web searches using Brave Search API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Brave Search service.
        
        Args:
            api_key: Brave Search API key. If not provided, uses BRAVE_SEARCH_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        if not self.api_key:
            raise ValueError("Brave Search API key not found. Set BRAVE_SEARCH_API_KEY environment variable.")
        
        # Initialize async client
        self.client = AsyncBrave(api_key=self.api_key)
    
    async def search_statute(self, citation: str, count: int = 5) -> List[Dict]:
        """
        Search for a statute on law.cornell.edu.
        
        Args:
            citation: The normalized statute citation (e.g., "11 U.S.C. § 363")
            count: Number of results to return
            
        Returns:
            List of search results with title, url, and description
        """
        try:
            # Format search query for law.cornell.edu
            search_query = f"site:law.cornell.edu {citation}"
            
            # Perform search
            response = await self.client.search(
                q=search_query,
                count=count,
                search_lang="en",
                country="US"
            )
            
            # Extract relevant results
            results = []
            if response.web_results:
                for result in response.web_results:
                    results.append({
                        'title': result.title,
                        'url': result.url,
                        'description': result.description,
                        'snippet': getattr(result, 'snippet', '')
                    })
            
            return results
            
        except Exception as e:
            print(f"Error searching for statute: {e}")
            return []
    
    async def search_case(self, case_info: str, count: int = 5) -> List[Dict]:
        """
        Search for a case on courtlistener.com/opinion.
        
        Args:
            case_info: The case search format (e.g., "Stern v. Marshall, U.S. Supreme Court, 2011")
            count: Number of results to return
            
        Returns:
            List of search results with title, url, and description
        """
        try:
            # Format search query for courtlistener.com
            search_query = f"site:courtlistener.com/opinion {case_info}"
            
            # Perform search
            response = await self.client.search(
                q=search_query,
                count=count,
                search_lang="en",
                country="US"
            )
            
            # Extract relevant results
            results = []
            if response.web_results:
                for result in response.web_results:
                    results.append({
                        'title': result.title,
                        'url': result.url,
                        'description': result.description,
                        'snippet': getattr(result, 'snippet', '')
                    })
            
            return results
            
        except Exception as e:
            print(f"Error searching for case: {e}")
            return []
    
    async def close(self):
        """Close the client session."""
        # The brave-search library handles session management internally
        pass