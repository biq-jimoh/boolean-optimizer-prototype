"""
Brave Search Service for web searches
Handles statute and case law searches using the Brave Search API.
"""

import os
from typing import List, Dict, Optional
import httpx
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
        
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
    
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
            
            params = {
                "q": search_query,
                "count": count,
                "search_lang": "en",
                "country": "US"
            }
            
            # Perform search
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
            
            # Extract relevant results
            data = response.json()
            results = []
            
            web_results = data.get("web", {}).get("results", [])
            for result in web_results:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'description': result.get('description', ''),
                    'snippet': result.get('snippet', '')
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
            
            params = {
                "q": search_query,
                "count": count,
                "search_lang": "en",
                "country": "US"
            }
            
            # Perform search
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
            
            # Extract relevant results
            data = response.json()
            results = []
            
            web_results = data.get("web", {}).get("results", [])
            for result in web_results:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'description': result.get('description', ''),
                    'snippet': result.get('snippet', '')
                })
            
            return results
            
        except Exception as e:
            print(f"Error searching for case: {e}")
            return []
    
    async def close(self):
        """Close the client session."""
        # No cleanup needed with httpx.AsyncClient context manager
        pass