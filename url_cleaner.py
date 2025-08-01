"""
URL Cleaning Utilities
Ensures we get the main opinion page, not subpaths like /authorities/
"""

from urllib.parse import urlparse, urlunparse
import re


def clean_courtlistener_url(url: str) -> str:
    """
    Clean a CourtListener URL to ensure we get the main opinion page.
    
    Examples:
    - https://www.courtlistener.com/opinion/219617/stern-v-marshall/authorities/?hc_location=ufi
      → https://www.courtlistener.com/opinion/219617/stern-v-marshall/
    - https://www.courtlistener.com/opinion/219617/stern-v-marshall/cited-by/
      → https://www.courtlistener.com/opinion/219617/stern-v-marshall/
    
    Args:
        url: The CourtListener URL to clean
        
    Returns:
        Cleaned URL pointing to the main opinion page
    """
    parsed = urlparse(url)
    
    # Check if this is a courtlistener.com URL
    if 'courtlistener.com' not in parsed.netloc:
        return url
    
    # Extract the path
    path = parsed.path
    
    # Pattern to match opinion URLs: /opinion/{id}/{case-name}/
    # We want to remove anything after the case name
    pattern = r'^(/opinion/\d+/[^/]+/).*'
    match = re.match(pattern, path)
    
    if match:
        # Get just the base opinion path
        clean_path = match.group(1)
        # Rebuild the URL with the clean path
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            clean_path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
    
    # If pattern doesn't match, return original URL
    return url
