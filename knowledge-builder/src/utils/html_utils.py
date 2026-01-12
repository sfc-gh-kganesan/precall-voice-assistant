"""
HTML utility functions for knowledge base analysis.

This module provides utilities for extracting and analyzing outbound links
from HTML content, useful for identifying knowledge leakage to external systems.
"""

import re
from urllib.parse import unquote, urlparse


def extract_domains_from_html(html_text: str) -> list[str]:
    """
    Extract unique domains from hrefs or https links in HTML, skipping malformed ones.

    This function parses HTML content to find external links and extracts their domains.
    It handles URL-encoded links, relative URLs, and malformed URLs gracefully.

    Args:
        html_text: The HTML content as a string

    Returns:
        A list of unique domain names (lowercased) found in the HTML

    Examples:
        >>> html = '<a href="https://example.com/page">Link</a>'
        >>> extract_domains_from_html(html)
        ['example.com']

        >>> html = '<a href="https://docs.google.com">Docs</a> Visit https://github.com'
        >>> sorted(extract_domains_from_html(html))
        ['docs.google.com', 'github.com']
    """
    if not isinstance(html_text, str) or not html_text:
        return []

    # Find href attributes and raw https links
    urls = re.findall(r'href=["\']?([^"\'>\s]+)', html_text, flags=re.IGNORECASE)
    urls += re.findall(r'https?://[^\s"\'>]+', html_text, flags=re.IGNORECASE)

    domains = []
    for raw in urls:
        try:
            u = unquote(raw.strip())

            # Add scheme if missing for www URLs
            if u.lower().startswith("www."):
                u = "https://" + u

            # Skip relative or malformed URLs
            if not u.lower().startswith(("http://", "https://")):
                continue

            parsed = urlparse(u)
            domain = parsed.netloc.lower()

            # Ignore empty or invalid hostnames
            if not domain or domain in ("server", "localhost"):
                continue

            domains.append(domain)

        except Exception:
            # Ignore malformed URLs silently
            # (e.g., ValueError: 'server' does not appear to be an IPv4 or IPv6 address)
            continue

    return list(set(domains))


def extract_domains_from_html_as_string(html_text: str) -> str:
    """
    Extract domains and return as comma-separated string (Snowflake UDF friendly).

    Args:
        html_text: The HTML content as a string

    Returns:
        Comma-separated string of unique domains, or empty string if none found

    Examples:
        >>> html = '<a href="https://example.com">Link</a>'
        >>> extract_domains_from_html_as_string(html)
        'example.com'
    """
    domains = extract_domains_from_html(html_text)
    return ",".join(sorted(domains)) if domains else ""
