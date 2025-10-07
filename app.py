import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
from typing import List, Dict, Set
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class CapillaryDocScraper:
    def __init__(self, base_url: str = "https://docs.capillarytech.com/"):
        self.base_url = base_url
        self.visited_urls: Set[str] = set()
        self.scraped_data: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to the documentation domain"""
        parsed = urlparse(url)
        base_parsed = urlparse(self.base_url)
        return parsed.netloc == base_parsed.netloc
    
    def extract_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract relevant content from a documentation page"""
        content = {
            'url': url,
            'title': '',
            'content': '',
            'headings': [],
            'code_snippets': [],
            'links': []
        }
        
        # Extract title
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            content['title'] = title_tag.get_text(strip=True)
        
        # Extract main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            # Extract text content
            content['content'] = main_content.get_text(separator=' ', strip=True)
            
            # Extract headings
            for heading in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                content['headings'].append({
                    'level': heading.name,
                    'text': heading.get_text(strip=True)
                })
            
            # Extract code snippets
            for code in main_content.find_all(['code', 'pre']):
                snippet = code.get_text(strip=True)
                if len(snippet) > 10:  # Filter out very short snippets
                    content['code_snippets'].append(snippet)
        
        return content
    
    def get_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract all valid documentation links from the page"""
        links = []
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(current_url, link['href'])
            # Remove fragments and query parameters for deduplication
            clean_url = absolute_url.split('#')[0].split('?')[0]
            if self.is_valid_url(clean_url) and clean_url not in self.visited_urls:
                links.append(clean_url)
        return links
    
    def scrape_page(self, url: str) -> bool:
        """Scrape a single page"""
        if url in self.visited_urls:
            return False
        
        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            content = self.extract_content(soup, url)
            
            if content['content']:  # Only save if content was found
                self.scraped_data.append(content)
            
            self.visited_urls.add(url)
            
            # Get and return new links
            return self.get_links(soup, url)
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return []
    
    def scrape_documentation(self, max_pages: int = 100, delay: float = 1.0):
        """Scrape documentation with BFS approach"""
        urls_to_visit = [self.base_url]
        pages_scraped = 0
        
        while urls_to_visit and pages_scraped < max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            new_links = self.scrape_page(current_url)
            if new_links:
                urls_to_visit.extend(new_links)
            
            pages_scraped += 1
            time.sleep(delay)  # Be respectful to the server
            
            if pages_scraped % 10 == 0:
                logger.info(f"Progress: {pages_scraped} pages scraped")
        
        logger.info(f"Scraping complete! Total pages: {len(self.scraped_data)}")
    
    def save_to_json(self, filename: str = 'capillary_docs.json'):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {filename}")

    def get_data(self) -> List[Dict]:
        """Return scraped data"""
        return self.scraped_data
    
if __name__ == "__main__":
    scraper = CapillaryDocScraper()
    scraper.scrape_documentation(max_pages=50, delay=1.5)
    scraper.save_to_json('capillary_docs.json')
    print(f"Scraped {len(scraper.scraped_data)} pages")