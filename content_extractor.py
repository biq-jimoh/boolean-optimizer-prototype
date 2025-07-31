"""
Content Extraction Module
Fetches and extracts relevant legal text from web pages.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional
import asyncio
import re


class ContentExtractor:
    """Extracts legal content from web pages."""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the content extractor.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; BankruptcyQueryOptimizer/1.0)'
        }
    
    async def extract_statute_text(self, url: str, subsection: Optional[str] = None) -> str:
        """
        Extract statute text from a law.cornell.edu page.
        
        Args:
            url: URL of the statute page
            subsection: Optional subsection to focus on (e.g., "(f)")
            
        Returns:
            Extracted statute text
        """
        try:
            # Fetch the page
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=True
                )
                response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find the main content area
            content = None
            
            # Look for common content containers on Cornell Law
            for selector in [
                '.content',
                '#content', 
                'div.field-name-body',
                'article',
                'main'
            ]:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem
                    break
            
            if not content:
                # Fallback to body
                content = soup.body
            
            # Extract text
            text = content.get_text(separator='\n', strip=True)
            
            # Clean up the text
            text = self._clean_statute_text(text)
            
            # If subsection specified, try to extract relevant portion
            if subsection:
                text = self._extract_subsection(text, subsection)
            
            # Limit length for context
            max_length = 3000
            if len(text) > max_length:
                # Try to keep the most relevant part
                text = self._truncate_statute_text(text, max_length, subsection)
            
            return text
            
        except Exception as e:
            print(f"Error extracting statute text from {url}: {e}")
            return f"Error fetching content: {str(e)}"
    
    async def extract_case_text(self, url: str) -> str:
        """
        Extract case opinion text from a courtlistener.com page.
        
        Args:
            url: URL of the case opinion page
            
        Returns:
            Extracted case text
        """
        try:
            # Fetch the page
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=True
                )
                response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find the opinion content
            content = None
            
            # Look for opinion content containers on CourtListener
            for selector in [
                '#opinion-content',
                '.opinion-text',
                'article.opinion',
                'div.plaintext',
                'pre.plaintext'
            ]:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem
                    break
            
            if not content:
                # Try to find any pre-formatted text
                pre_elems = soup.find_all('pre')
                if pre_elems:
                    content = pre_elems[0]
            
            if not content:
                # Fallback to main content area
                content = soup.select_one('main') or soup.body
            
            # Extract text
            text = content.get_text(separator='\n', strip=True)
            
            # Clean up the text
            text = self._clean_case_text(text)
            
            # Limit length for context
            max_length = 4000
            if len(text) > max_length:
                # Try to get the beginning which usually has key info
                text = text[:max_length] + "\n\n[... truncated for length ...]"
            
            return text
            
        except Exception as e:
            print(f"Error extracting case text from {url}: {e}")
            return f"Error fetching content: {str(e)}"
    
    def _clean_statute_text(self, text: str) -> str:
        """Clean up statute text."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove common navigation elements
        lines = text.split('\n')
        cleaned_lines = []
        skip_patterns = [
            r'^(Home|Search|Menu|Navigation)',
            r'^U\.S\. Code Toolbox',
            r'^(Previous|Next|Up)',
            r'^Cornell Law School'
        ]
        
        for line in lines:
            if not any(re.match(pattern, line.strip(), re.I) for pattern in skip_patterns):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _clean_case_text(self, text: str) -> str:
        """Clean up case opinion text."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove line numbers if present
        text = re.sub(r'^\s*\d+\s+', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _extract_subsection(self, text: str, subsection: str) -> str:
        """Try to extract a specific subsection from statute text."""
        # Clean subsection format
        subsection = subsection.strip('()')
        
        # Try to find the subsection
        patterns = [
            rf'\({subsection}\)[^\(]*',  # (f) followed by content
            rf'\({subsection}\).*?(?=\([a-z]\)|$)',  # Until next subsection
            rf'{subsection}\.[^\(]*'  # Alternative format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Get some context before and after
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 500)
                return text[start:end]
        
        # If not found, return the full text
        return text
    
    def _truncate_statute_text(self, text: str, max_length: int, subsection: Optional[str]) -> str:
        """Intelligently truncate statute text to stay within limits."""
        if subsection and subsection in text:
            # Try to keep the subsection visible
            idx = text.find(subsection)
            start = max(0, idx - max_length // 2)
            end = min(len(text), start + max_length)
            return text[start:end] + "\n\n[... truncated for length ...]"
        else:
            # Just take from the beginning
            return text[:max_length] + "\n\n[... truncated for length ...]"