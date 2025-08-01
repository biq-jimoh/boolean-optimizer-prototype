"""
Brave Search Service for web searches
Handles statute and case law searches using the Brave Search API.
Includes exponential backoff for rate limit handling.
"""

import os
from typing import List, Dict, Optional
import httpx
import asyncio
import time
import random


class BraveSearchService:
    """Service for performing web searches using Brave Search API."""
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, 
                 initial_backoff: float = 1.0, max_backoff: float = 60.0):
        """
        Initialize the Brave Search service.
        
        Args:
            api_key: Brave Search API key. If not provided, uses BRAVE_SEARCH_API_KEY env var.
            max_retries: Maximum number of retry attempts for 429 errors (default: 3)
            initial_backoff: Initial backoff delay in seconds (default: 1.0)
            max_backoff: Maximum backoff delay in seconds (default: 60.0)
        """
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        if not self.api_key:
            raise ValueError("Brave Search API key not found. Set BRAVE_SEARCH_API_KEY environment variable.")
        
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        
        # Retry configuration
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
    
    async def _execute_with_retry(self, url: str, params: dict) -> Optional[httpx.Response]:
        """
        Execute HTTP request with exponential backoff retry for 429 errors.
        
        Args:
            url: The URL to request
            params: Query parameters
            
        Returns:
            Response object if successful, None if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers=self.headers,
                        params=params,
                        timeout=30.0
                    )
                    
                    # If successful, return response
                    if response.status_code != 429:
                        response.raise_for_status()
                        return response
                    
                    # Handle 429 Too Many Requests
                    if attempt < self.max_retries:
                        # Calculate backoff with exponential increase and jitter
                        backoff = min(
                            self.initial_backoff * (2 ** attempt) + random.uniform(0, 0.1),
                            self.max_backoff
                        )
                        
                        # Check for Retry-After header
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                backoff = max(float(retry_after), backoff)
                            except ValueError:
                                pass
                        
                        print(f"Rate limited (429). Retrying in {backoff:.1f} seconds... (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(backoff)
                    else:
                        # Final attempt failed
                        response.raise_for_status()
                        
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code != 429 or attempt == self.max_retries:
                    # Re-raise if not 429 or if we've exhausted retries
                    raise
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    raise
                    
        return None
    
    async def search_statute(self, citation: str, count: int = 5) -> List[Dict]:
        """
        Search for a statute on law.cornell.edu with automatic retry for rate limits.
        
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
            
            # Perform search with retry
            response = await self._execute_with_retry(self.base_url, params)
            if not response:
                print(f"Failed to search for statute after {self.max_retries} retries")
                return []
            
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
        Search for a case on courtlistener.com/opinion with automatic retry for rate limits.
        
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
            
            # Perform search with retry
            response = await self._execute_with_retry(self.base_url, params)
            if not response:
                print(f"Failed to search for case after {self.max_retries} retries")
                return []
            
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