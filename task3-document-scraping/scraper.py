"""
Document Scraper for PDF Extraction

This script scrapes web pages for PDF links, downloads PDFs, extracts metadata
and text content, and saves results in JSON format.

Author: Document Scraping
Date: 2025-11-25
"""

import requests
from bs4 import BeautifulSoup
import PyPDF2
import json
import logging
import time
import os
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re
from urllib.parse import unquote

# Selenium imports for 403 fallback
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium/undetected-chromedriver not available. 403 fallback disabled.")


# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DocumentScraper:
    """
    Web scraper for extracting PDF documents and metadata.
    
    Features:
    - Ethical scraping with rate limiting
    - PDF download and text extraction
    - Metadata extraction
    - Comprehensive error handling
    """
    
    def __init__(self, delay: float = 2.0, max_pdfs: int = 3):
        """
        Initialize the document scraper.
        
        Args:
            delay: Delay between requests in seconds (default: 2.0)
            max_pdfs: Maximum number of PDFs to download per URL (default: 3)
        """
        self.delay = delay
        self.max_pdfs = max_pdfs
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.downloads_dir = 'downloads'
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.driver = None  # Selenium driver (lazy initialization)
        
        logger.info(f"Initialized DocumentScraper (delay={delay}s, max_pdfs={max_pdfs})")
    
    def scrape_url(self, url: str) -> List[Dict]:
        """
        Scrape a single URL for PDF documents.
        
        Args:
            url: URL to scrape
            
        Returns:
            List of document dictionaries with metadata
        """
        logger.info(f"Scraping URL: {url}")
        documents = []
        
        try:
            # Fetch the page
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract PDF links
            pdf_links = self.extract_pdf_links(soup, url)
            logger.info(f"Found {len(pdf_links)} PDF links on main page")
            
            # If no PDFs found, try crawling one level deeper
            if len(pdf_links) == 0:
                logger.info("No PDFs on main page, crawling subpages...")
                pdf_links = self.crawl_for_pdfs(soup, url, max_subpages=5)
                logger.info(f"Found {len(pdf_links)} PDF links after crawling subpages")
            
            # Process PDFs (limit to max_pdfs)
            for i, pdf_info in enumerate(pdf_links[:self.max_pdfs]):
                logger.info(f"Processing PDF {i+1}/{min(len(pdf_links), self.max_pdfs)}: {pdf_info['url']}")
                
                try:
                    # Extract metadata and download PDF
                    document = self.process_pdf(pdf_info, url)
                    if document:
                        documents.append(document)
                    
                    # Rate limiting
                    if i < min(len(pdf_links), self.max_pdfs) - 1:
                        time.sleep(self.delay)
                        
                except Exception as e:
                    logger.error(f"Error processing PDF {pdf_info['url']}: {e}")
                    continue
            
        except requests.HTTPError as e:
            # Check for 403 Forbidden error
            if e.response.status_code == 403:
                logger.warning(f"403 Forbidden error for {url}. Attempting Selenium fallback...")
                return self.scrape_url_with_selenium(url)
            else:
                logger.error(f"HTTP error fetching URL {url}: {e}")
        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
        
        return documents
    
    def extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Extract PDF links from HTML.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of dictionaries with URL and title
        """
        pdf_links = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Check if link points to PDF
            if href.lower().endswith('.pdf') or '.pdf' in href.lower():
                # Resolve relative URLs
                full_url = urljoin(base_url, href)
                
                # Extract title from link text or filename
                title = link.get_text(strip=True)
                if not title:
                    # Extract from filename
                    title = os.path.basename(urlparse(full_url).path)
                
                pdf_links.append({
                    'url': full_url,
                    'title': title
                })
        
        return pdf_links
    
    def crawl_for_pdfs(self, soup: BeautifulSoup, base_url: str, max_subpages: int = 5) -> List[Dict]:
        """
        Crawl subpages to find PDF links when none found on main page.
        
        Args:
            soup: BeautifulSoup object of main page
            base_url: Base URL for resolving relative links
            max_subpages: Maximum number of subpages to check
            
        Returns:
            List of dictionaries with URL and title
        """
        pdf_links = []
        subpages_checked = 0
        
        # Find promising subpage links (publications, documents, reports, etc.)
        # keywords = ['publication', 'document', 'report', 'download', 'resource', 'file']
        
        for link in soup.find_all('a', href=True):
            if subpages_checked >= max_subpages:
                break
                
            href = link['href']
            link_text = link.get_text(strip=True).lower()
            
            # Skip if already a PDF
            if href.lower().endswith('.pdf'):
                continue
            
            try:
                # Resolve URL
                full_url = urljoin(base_url, href)
                
                # Skip external domains
                if urlparse(full_url).netloc != urlparse(base_url).netloc:
                    continue
                
                logger.info(f"Checking subpage: {full_url}")
                
                # Fetch subpage
                time.sleep(self.delay)  # Rate limiting
                response = self.session.get(full_url, timeout=10)
                response.raise_for_status()
                
                # Parse and extract PDFs
                sub_soup = BeautifulSoup(response.content, 'lxml')
                sub_pdfs = self.extract_pdf_links(sub_soup, full_url)
                
                if sub_pdfs:
                    logger.info(f"Found {len(sub_pdfs)} PDFs on subpage")
                    pdf_links.extend(sub_pdfs)
                    
                    # Stop if we have enough
                    if len(pdf_links) >= self.max_pdfs:
                        break
                
                subpages_checked += 1
                
            except Exception as e:
                logger.warning(f"Error checking subpage {full_url}: {e}")
                continue
        
        return pdf_links
    
    def scrape_url_with_selenium(self, url: str) -> List[Dict]:
        """
        Scrape URL using Selenium with undetected-chromedriver (fallback for 403 errors).
        
        Args:
            url: URL to scrape
            
        Returns:
            List of document dictionaries with metadata
        """
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium not available. Cannot use 403 fallback.")
            return []
        
        logger.info(f"Using Selenium to scrape: {url}")
        documents = []
        
        try:
            # Initialize driver if not already done
            if self.driver is None:
                logger.info("Initializing undetected Chrome driver...")
                options = uc.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                self.driver = uc.Chrome(options=options)
            
            # Navigate to URL
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Get page source and parse
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            
            # Extract PDF links
            pdf_links = self.extract_pdf_links(soup, url)
            logger.info(f"Found {len(pdf_links)} PDF links with Selenium")
            
            # If no PDFs found, try crawling
            if len(pdf_links) == 0:
                logger.info("No PDFs found, attempting to crawl subpages with Selenium...")
                # Note: Crawling with Selenium would be slower, so we limit it
                # For now, just return empty list
                logger.warning("Subpage crawling with Selenium not implemented")
            
            # Process PDFs (limit to max_pdfs)
            for i, pdf_info in enumerate(pdf_links[:self.max_pdfs]):
                logger.info(f"Processing PDF {i+1}/{min(len(pdf_links), self.max_pdfs)}: {pdf_info['url']}")
                
                try:
                    # Extract metadata and download PDF
                    document = self.process_pdf(pdf_info, url)
                    if document:
                        documents.append(document)
                    
                    # Rate limiting
                    if i < min(len(pdf_links), self.max_pdfs) - 1:
                        time.sleep(self.delay)
                        
                except Exception as e:
                    logger.error(f"Error processing PDF {pdf_info['url']}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping with Selenium {url}: {e}")
        
        return documents
    
    def close(self):
        """Explicitly close the Selenium driver."""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
    
    def process_pdf(self, pdf_info: Dict, source_url: str) -> Optional[Dict]:
        """
        Download PDF and extract metadata and content.
        
        Args:
            pdf_info: Dictionary with PDF URL and title
            source_url: Source page URL
            
        Returns:
            Document dictionary with metadata or None if failed
        """
        pdf_url = pdf_info['url']
        
        try:
            # Download PDF
            response = self.session.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Get file size from headers
            size_bytes = response.headers.get('Content-Length')
            size_kb = int(size_bytes) / 1024 if size_bytes else None
            
            # Save PDF temporarily
            filename = os.path.basename(urlparse(pdf_url).path)
            if not filename.endswith('.pdf'):
                filename = f"document_{hash(pdf_url)}.pdf"
            
            # Decode URL-encoded filename (e.g., %D0%97 → Cyrillic characters)
            try:
                filename = unquote(filename)
            except:
                logger.info(f"Error decoding filename: {filename}. Attempting to process with original filename.")
                pass
            
            # Truncate filename if too long (Windows path limit issues)
            if len(filename) > 100:
                # Keep extension, truncate name
                name, ext = os.path.splitext(filename)
                filename = name[:96] + ext  # 96 + ".pdf" = 100
                logger.info(f"Filename truncated to 100 characters: {filename}")
            
            pdf_path = os.path.join(self.downloads_dir, filename)
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded PDF: {filename}")
            
            # Extract text content
            content_preview = self.extract_pdf_text(pdf_path)
            
            # Extract publication date from URL or filename if possible
            date_published = self.extract_date(pdf_url, pdf_info['title'])
            
            # Build document metadata
            document = {
                'title': pdf_info['title'] or filename,
                'url': pdf_url,
                'size_kb': round(size_kb, 2) if size_kb else None,
                'date_published': date_published,
                'content_preview': content_preview,
                'scraped_at': datetime.now().isoformat()
            }
            
            return document
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_url}: {e}")
            return None
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """
        Extract text content from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            First 500 characters of text content
        """
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Extract text from all pages
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                # Clean up text
                text = ' '.join(text.split())
                
                # Return first 500 characters
                preview = text[:500] if len(text) > 500 else text
                
                logger.info(f"Extracted {len(text)} characters from PDF")
                return preview
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""
    
    def extract_date(self, url: str, title: str) -> Optional[str]:
        """
        Try to extract publication date from URL or title.
        
        Args:
            url: PDF URL
            title: PDF title
            
        Returns:
            Date string in YYYY-MM-DD format or None
        """
        # Look for date patterns in URL and title
        text = f"{url} {title}"
        
        # Pattern: YYYY-MM-DD or YYYY/MM/DD
        pattern1 = r'(\d{4})[-/](\d{2})[-/](\d{2})'
        match = re.search(pattern1, text)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        
        # Pattern: YYYY
        pattern2 = r'(20\d{2})'
        match = re.search(pattern2, text)
        if match:
            return f"{match.group(1)}-01-01"  # Default to January 1st
        
        return None
    
    def scrape_urls(self, urls: List[str]) -> List[Dict]:
        """
        Scrape multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of all documents found
        """
        all_documents = []
        
        for i, url in enumerate(urls):
            logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
            
            documents = self.scrape_url(url)
            all_documents.extend(documents)
            
            # Rate limiting between URLs
            if i < len(urls) - 1:
                logger.info(f"Waiting {self.delay} seconds before next URL...")
                time.sleep(self.delay)
        
        return all_documents
    
    def save_results(self, documents: List[Dict], output_file: str = 'extracted_documents.json'):
        """
        Save scraped documents to JSON file.
        
        Args:
            documents: List of document dictionaries
            output_file: Output file path
        """
        logger.info(f"Saving {len(documents)} documents to {output_file}")
        
        output_data = {
            'documents': documents
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved results to {output_file}")


def load_urls_from_file(filename: str) -> List[str]:
    """
    Load URLs from text file.
    
    Args:
        filename: Path to file containing URLs
        
    Returns:
        List of URLs
    """
    urls = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    urls.append(line)
    except FileNotFoundError:
        logger.error(f"URL file not found: {filename}")
    
    return urls


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("Document Scraper Started")
    logger.info("=" * 80)
    
    # Load URLs from file
    urls = load_urls_from_file('sample_urls.txt')
    
    if not urls:
        logger.error("No URLs to scrape")
        return
    
    logger.info(f"Loaded {len(urls)} URLs to scrape")
    
    # Initialize scraper
    scraper = DocumentScraper(delay=2.0, max_pdfs=3)
    
    # Scrape URLs
    documents = scraper.scrape_urls(urls)
    
    # Save results
    scraper.save_results(documents)
    
    logger.info("=" * 80)
    logger.info(f"Scraping completed. Found {len(documents)} documents.")
    logger.info("=" * 80)

    scraper.close()


if __name__ == '__main__':
    main()
