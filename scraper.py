"""
Web Scraper Module
Uses BeautifulSoup4 and requests for fast, efficient web scraping.
"""

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin, urlparse
from typing import Optional
import re


class WebScraper:
    """A web scraper that extracts content and converts it to structured markdown."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content of a page."""
        try:
            response = self.session.get(
                url, 
                timeout=self.timeout,
                allow_redirects=True,
                verify=True
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'Unknown'
            if status_code == 404:
                raise Exception(f"Page not found (404): The URL '{url}' does not exist")
            elif status_code == 403:
                raise Exception(f"Access forbidden (403): The website blocked access to '{url}'")
            elif status_code == 401:
                raise Exception(f"Unauthorized (401): This page requires authentication")
            elif status_code == 500:
                raise Exception(f"Server error (500): The website encountered an internal error")
            elif status_code == 503:
                raise Exception(f"Service unavailable (503): The website is temporarily down")
            else:
                raise Exception(f"HTTP Error {status_code}: Failed to fetch '{url}'")
        except requests.exceptions.SSLError:
            raise Exception(f"SSL Error: Could not establish secure connection to '{url}'")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Connection failed: Could not connect to '{url}'. Check if the URL is correct.")
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout: The website took too long to respond")
        except requests.exceptions.TooManyRedirects:
            raise Exception(f"Too many redirects: The URL has a redirect loop")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")
    
    def scrape(self, url: str) -> dict:
        """
        Scrape a URL and return structured content.
        
        Returns:
            dict with 'title', 'url', 'markdown', and 'text' keys
        """
        html = self.fetch_page(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe']):
            element.decompose()
        
        # Extract title
        title = self._extract_title(soup)
        
        # Find main content area
        main_content = self._find_main_content(soup)
        
        # Convert to markdown preserving structure
        markdown = self._to_markdown(main_content, url)
        
        # Also get plain text
        text = self._get_plain_text(main_content)
        
        return {
            'title': title,
            'url': url,
            'markdown': markdown,
            'text': text
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        # Try og:title first
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # Try regular title
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        return "Untitled Page"
    
    def _find_main_content(self, soup: BeautifulSoup) -> Tag:
        """Find the main content area of the page."""
        # Priority order for content containers
        selectors = [
            'main',
            'article',
            '[role="main"]',
            '#content',
            '#main-content',
            '.content',
            '.main-content',
            '.post-content',
            '.article-content',
            '.entry-content',
        ]
        
        for selector in selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 100:
                return content
        
        # Fallback to body
        body = soup.find('body')
        return body if body else soup
    
    def _to_markdown(self, element: Tag, base_url: str, depth: int = 0) -> str:
        """Convert HTML element to markdown preserving structure."""
        if element is None:
            return ""
        
        markdown_parts = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child)
                # Collapse whitespace but preserve single spaces
                text = re.sub(r'\s+', ' ', text)
                if text.strip():
                    markdown_parts.append(text)
            elif isinstance(child, Tag):
                md = self._tag_to_markdown(child, base_url, depth)
                if md:
                    markdown_parts.append(md)
        
        result = ''.join(markdown_parts)
        # Clean up excessive newlines
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()
    
    def _tag_to_markdown(self, tag: Tag, base_url: str, depth: int) -> str:
        """Convert a single tag to markdown."""
        tag_name = tag.name.lower()
        
        # Headings
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            text = tag.get_text(strip=True)
            if text:
                return f"\n\n{'#' * level} {text}\n\n"
            return ""
        
        # Paragraphs
        if tag_name == 'p':
            text = self._to_markdown(tag, base_url, depth)
            if text.strip():
                return f"\n\n{text.strip()}\n\n"
            return ""
        
        # Line breaks
        if tag_name == 'br':
            return "\n"
        
        # Horizontal rules
        if tag_name == 'hr':
            return "\n\n---\n\n"
        
        # Bold
        if tag_name in ['strong', 'b']:
            text = tag.get_text(strip=True)
            if text:
                return f"**{text}**"
            return ""
        
        # Italic
        if tag_name in ['em', 'i']:
            text = tag.get_text(strip=True)
            if text:
                return f"*{text}*"
            return ""
        
        # Code
        if tag_name == 'code':
            text = tag.get_text()
            if '\n' in text:
                return f"\n```\n{text}\n```\n"
            return f"`{text}`"
        
        # Preformatted / Code blocks
        if tag_name == 'pre':
            code = tag.find('code')
            if code:
                text = code.get_text()
            else:
                text = tag.get_text()
            lang = ""
            if code and code.get('class'):
                for cls in code.get('class', []):
                    if cls.startswith('language-'):
                        lang = cls.replace('language-', '')
                        break
            return f"\n\n```{lang}\n{text}\n```\n\n"
        
        # Links
        if tag_name == 'a':
            href = tag.get('href', '')
            text = tag.get_text(strip=True)
            if href and text:
                # Make absolute URL
                full_url = urljoin(base_url, href)
                return f"[{text}]({full_url})"
            elif text:
                return text
            return ""
        
        # Images
        if tag_name == 'img':
            src = tag.get('src', '')
            alt = tag.get('alt', 'image')
            if src:
                full_url = urljoin(base_url, src)
                return f"![{alt}]({full_url})"
            return ""
        
        # Unordered lists
        if tag_name == 'ul':
            items = []
            for li in tag.find_all('li', recursive=False):
                item_text = self._to_markdown(li, base_url, depth + 1)
                if item_text.strip():
                    # Handle nested content
                    lines = item_text.strip().split('\n')
                    first_line = lines[0]
                    rest = '\n'.join('  ' + line for line in lines[1:] if line.strip())
                    item = f"{'  ' * depth}- {first_line}"
                    if rest:
                        item += '\n' + rest
                    items.append(item)
            if items:
                return "\n\n" + '\n'.join(items) + "\n\n"
            return ""
        
        # Ordered lists
        if tag_name == 'ol':
            items = []
            start = int(tag.get('start', 1))
            for i, li in enumerate(tag.find_all('li', recursive=False), start=start):
                item_text = self._to_markdown(li, base_url, depth + 1)
                if item_text.strip():
                    lines = item_text.strip().split('\n')
                    first_line = lines[0]
                    rest = '\n'.join('   ' + line for line in lines[1:] if line.strip())
                    item = f"{'  ' * depth}{i}. {first_line}"
                    if rest:
                        item += '\n' + rest
                    items.append(item)
            if items:
                return "\n\n" + '\n'.join(items) + "\n\n"
            return ""
        
        # Definition lists
        if tag_name == 'dl':
            parts = []
            for child in tag.children:
                if isinstance(child, Tag):
                    if child.name == 'dt':
                        text = child.get_text(strip=True)
                        parts.append(f"\n**{text}**")
                    elif child.name == 'dd':
                        text = self._to_markdown(child, base_url, depth)
                        parts.append(f"\n: {text.strip()}")
            if parts:
                return "\n" + ''.join(parts) + "\n"
            return ""
        
        # Blockquotes
        if tag_name == 'blockquote':
            text = self._to_markdown(tag, base_url, depth)
            if text.strip():
                lines = text.strip().split('\n')
                quoted = '\n'.join(f"> {line}" for line in lines)
                return f"\n\n{quoted}\n\n"
            return ""
        
        # Tables
        if tag_name == 'table':
            return self._table_to_markdown(tag, base_url)
        
        # Divs, spans, and other containers - process children
        if tag_name in ['div', 'span', 'section', 'article', 'main', 'figure', 'figcaption']:
            return self._to_markdown(tag, base_url, depth)
        
        # Default: just get the text content
        return self._to_markdown(tag, base_url, depth)
    
    def _table_to_markdown(self, table: Tag, base_url: str) -> str:
        """Convert an HTML table to markdown."""
        rows = []
        
        # Get headers
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [self._to_markdown(th, base_url, 0).strip() or ' ' 
                          for th in header_row.find_all(['th', 'td'])]
        
        # Get body rows
        tbody = table.find('tbody') or table
        body_rows = []
        for tr in tbody.find_all('tr'):
            cells = [self._to_markdown(td, base_url, 0).strip() or ' ' 
                    for td in tr.find_all(['td', 'th'])]
            if cells:
                # If no headers yet and first row has th elements, use as headers
                if not headers and tr.find('th'):
                    headers = cells
                else:
                    body_rows.append(cells)
        
        if not headers and body_rows:
            headers = body_rows.pop(0)
        
        if not headers:
            return ""
        
        # Build markdown table
        col_count = len(headers)
        rows.append('| ' + ' | '.join(headers) + ' |')
        rows.append('| ' + ' | '.join(['---'] * col_count) + ' |')
        
        for row in body_rows:
            # Pad row to match header count
            while len(row) < col_count:
                row.append(' ')
            rows.append('| ' + ' | '.join(row[:col_count]) + ' |')
        
        return "\n\n" + '\n'.join(rows) + "\n\n"
    
    def _get_plain_text(self, element: Tag) -> str:
        """Get plain text content from element."""
        if element is None:
            return ""
        
        text = element.get_text(separator='\n', strip=True)
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()


def scrape_url(url: str) -> dict:
    """
    Convenience function to scrape a URL.
    
    Args:
        url: The URL to scrape
        
    Returns:
        dict with 'title', 'url', 'markdown', and 'text' keys
    """
    scraper = WebScraper()
    return scraper.scrape(url)


if __name__ == "__main__":
    # Test the scraper
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://example.com"
    
    result = scrape_url(url)
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print("\n--- Markdown Output ---\n")
    print(result['markdown'])