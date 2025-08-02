"""
Content Extraction Module - Enhanced Browser-like Version
Uses browser-like headers, HTTP/2, delays, and Playwright fallback for WAF bypass.
"""

from typing import Optional
import httpx
import asyncio
from urllib.parse import urlparse
from token_budget import TokenBudgetConfig

# Try to import Playwright, but don't fail if it's not available
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Note: Playwright not available. Install with 'pip install playwright && playwright install chromium' for better WAF bypass.")


class ContentExtractor:
    """Fetches web pages with browser-like behavior for validation."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.token_config = TokenBudgetConfig()
        
        # Full set of Chrome headers in the order a real browser sends them
        self.base_headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def _get_headers_for_url(self, url: str) -> dict:
        """Get headers with proper Host header for the URL."""
        parsed = urlparse(url)
        headers = self.base_headers.copy()
        headers['Host'] = parsed.netloc
        
        # Adjust headers for specific sites
        if 'courtlistener.com' in url:
            headers['Referer'] = 'https://www.google.com/'
            headers['Sec-Fetch-Site'] = 'cross-site'
        
        return headers
    
    def truncate_to_token_limit(self, content: str, max_tokens: int) -> str:
        """
        Simple truncation to fit within token limit.
        
        Args:
            content: The content to truncate
            max_tokens: Maximum number of tokens allowed
            
        Returns:
            Truncated content that fits within token limit
        """
        estimated_tokens = self.token_config.estimate_tokens(content)
        
        if estimated_tokens <= max_tokens:
            return content
        
        # Simple character-based truncation
        max_chars = max_tokens * 4  # 1 token ≈ 4 chars
        return content[:max_chars] + "\n<!-- Content truncated due to token limit -->"
    
    async def _fetch_with_httpx(self, url: str) -> tuple[str, bool]:
        """
        Primary method: Fetch with enhanced httpx settings.
        
        Returns:
            Tuple of (content, success_bool)
        """
        try:
            headers = self._get_headers_for_url(url)
            
            async with httpx.AsyncClient(
                http2=True,  # Use HTTP/2 like modern browsers
                follow_redirects=True,
                verify=True,  # Verify SSL certificates
            ) as client:
                response = await client.get(
                    url, 
                    headers=headers,
                    timeout=self.timeout,
                )
                
                # Check for WAF challenges
                if response.status_code == 202 and response.headers.get('x-amzn-waf-action') == 'challenge':
                    print(f"WAF challenge detected for {url}")
                    return "WAF_CHALLENGE", False
                
                response.raise_for_status()
                print(f"Successfully fetched {url} with httpx (status: {response.status_code})")
                return response.text, True
                
        except Exception as e:
            print(f"Error with httpx fetch from {url}: {e}")
            return f"Error: {str(e)}", False
    
    async def _fetch_with_playwright(self, url: str) -> tuple[str, bool]:
        """
        Fallback method: Fetch using real browser automation.
        
        Returns:
            Tuple of (content, success_bool)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright not available for fallback", False
        
        try:
            print(f"Attempting Playwright fetch for {url}")
            
            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                # Create new page with browser context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # Navigate to the URL
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait a bit for any dynamic content
                await page.wait_for_timeout(1000)
                
                # Get the page content
                content = await page.content()
                
                await browser.close()
                
                print(f"Successfully fetched {url} with Playwright")
                return content, True
                
        except Exception as e:
            print(f"Error with Playwright fetch from {url}: {e}")
            return f"Error with Playwright: {str(e)}", False
    
    async def extract_statute_text(self, url: str, subsection: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        """
        Fetch the raw HTML content from a statute page with optional token limit.
        
        Args:
            url: URL of the statute page
            subsection: Subsection if specified (we'll let the validator handle this)
            max_tokens: Maximum tokens to return (optional)
            
        Returns:
            Raw HTML content, possibly truncated to fit token limit
        """
        # Try httpx first
        content, success = await self._fetch_with_httpx(url)
        
        # If WAF challenge detected, try Playwright
        if not success and content == "WAF_CHALLENGE":
            print(f"WAF challenge for statute {url}, trying Playwright...")
            content, success = await self._fetch_with_playwright(url)
        
        # Apply token limit if specified
        if max_tokens and success:
            content = self.truncate_to_token_limit(content, max_tokens)
        
        return content
    
    async def extract_case_text(self, url: str, max_tokens: Optional[int] = None) -> str:
        """
        Fetch the raw HTML content from a case opinion page with optional token limit.
        
        Args:
            url: URL of the case opinion page
            max_tokens: Maximum tokens to return (optional)
            
        Returns:
            Raw HTML content, possibly truncated to fit token limit
        """
        # Try httpx first
        content, success = await self._fetch_with_httpx(url)
        
        # If WAF challenge detected, try Playwright
        if not success and content == "WAF_CHALLENGE":
            print(f"WAF challenge for case {url}, trying Playwright...")
            content, success = await self._fetch_with_playwright(url)
        
        # Apply token limit if specified
        if max_tokens and success:
            content = self.truncate_to_token_limit(content, max_tokens)
        
        return content
