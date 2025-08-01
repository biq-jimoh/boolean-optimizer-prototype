"""
Content Extraction Module - Simplified Version with Error Handling
Just fetches raw HTML for the validator to analyze.
"""

from typing import Optional
import httpx


class ContentExtractor:
    """Fetches web pages for validation."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; BankruptcyQueryOptimizer/1.0)'
        }
    
    async def extract_statute_text(self, url: str, subsection: Optional[str] = None) -> str:
        """
        Fetch the raw HTML content from a statute page.
        
        Args:
            url: URL of the statute page
            subsection: Subsection if specified (we'll let the validator handle this)
            
        Returns:
            Raw HTML content
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=True
                )
                response.raise_for_status()
            
            # Check for WAF challenges
            if response.status_code == 202 and response.headers.get('x-amzn-waf-action') == 'challenge':
                return "Error: WAF challenge detected. The website is blocking automated requests."
            
            return response.text
            
        except Exception as e:
            print(f"Error fetching statute from {url}: {e}")
            return f"Error fetching content: {str(e)}"
    
    async def extract_case_text(self, url: str) -> str:
        """
        Fetch the raw HTML content from a case opinion page.
        
        Args:
            url: URL of the case opinion page
            
        Returns:
            Raw HTML content
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=True
                )
                
                # Check for WAF challenges
                if response.status_code == 202 and response.headers.get('x-amzn-waf-action') == 'challenge':
                    return "Error: WAF challenge detected. CourtListener is blocking automated requests."
                
                response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            print(f"Error fetching case from {url}: {e}")
            return f"Error fetching content: {str(e)}"
