"""
Unit Tests for Document Scraper

Tests scraping logic, PDF extraction, metadata collection, and error handling.

Author: Document Scraping Tests
Date: 2025-11-25
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
from scraper import DocumentScraper, load_urls_from_file
import requests


@pytest.fixture
def scraper():
    """Create a test scraper instance."""
    return DocumentScraper(delay=0.1, max_pdfs=2)


@pytest.fixture
def sample_html():
    """Sample HTML with PDF links."""
    return """
    <html>
        <body>
            <a href="/documents/report2024.pdf">Annual Report 2024</a>
            <a href="https://example.com/docs/financial_statement.pdf">Financial Statement</a>
            <a href="budget.pdf">Budget Document</a>
            <a href="/page.html">Regular Link</a>
        </body>
    </html>
    """


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content (minimal valid PDF)."""
    # Minimal PDF header
    return b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF'


@pytest.fixture(autouse=True)
def cleanup_downloads():
    """Clean up downloads directory after each test."""
    yield
    # Cleanup
    if os.path.exists('downloads'):
        for file in os.listdir('downloads'):
            try:
                os.remove(os.path.join('downloads', file))
            except:
                pass


class TestInitialization:
    """Test scraper initialization."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        scraper = DocumentScraper()
        assert scraper.delay == 2.0
        assert scraper.max_pdfs == 3
        assert 'User-Agent' in scraper.session.headers
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        scraper = DocumentScraper(delay=1.5, max_pdfs=5)
        assert scraper.delay == 1.5
        assert scraper.max_pdfs == 5
    
    def test_downloads_directory_created(self, scraper):
        """Test that downloads directory is created."""
        assert os.path.exists(scraper.downloads_dir)


class TestPDFLinkExtraction:
    """Test PDF link extraction from HTML."""
    
    def test_extract_pdf_links(self, scraper, sample_html):
        """Test extracting PDF links from HTML."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html, 'lxml')
        
        pdf_links = scraper.extract_pdf_links(soup, 'https://example.com')
        
        # Should find 3 PDF links
        assert len(pdf_links) == 3
        
        # Check URLs are resolved
        assert any('report2024.pdf' in link['url'] for link in pdf_links)
        assert any('financial_statement.pdf' in link['url'] for link in pdf_links)
        assert any('budget.pdf' in link['url'] for link in pdf_links)
    
    def test_extract_pdf_links_with_titles(self, scraper, sample_html):
        """Test that titles are extracted from link text."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html, 'lxml')
        
        pdf_links = scraper.extract_pdf_links(soup, 'https://example.com')
        
        # Check titles
        titles = [link['title'] for link in pdf_links]
        assert 'Annual Report 2024' in titles
        assert 'Financial Statement' in titles
    
    def test_extract_pdf_links_empty_html(self, scraper):
        """Test extraction from HTML with no PDF links."""
        from bs4 import BeautifulSoup
        html = "<html><body><a href='/page.html'>Link</a></body></html>"
        soup = BeautifulSoup(html, 'lxml')
        
        pdf_links = scraper.extract_pdf_links(soup, 'https://example.com')
        assert len(pdf_links) == 0


class TestDateExtraction:
    """Test date extraction from URLs and titles."""
    
    def test_extract_date_from_url_with_dashes(self, scraper):
        """Test extracting date in YYYY-MM-DD format."""
        url = "https://example.com/report-2024-03-15.pdf"
        date = scraper.extract_date(url, "")
        assert date == "2024-03-15"
    
    def test_extract_date_from_url_with_slashes(self, scraper):
        """Test extracting date in YYYY/MM/DD format."""
        url = "https://example.com/docs/2024/03/15/report.pdf"
        date = scraper.extract_date(url, "")
        assert date == "2024-03-15"
    
    def test_extract_year_only(self, scraper):
        """Test extracting year only."""
        url = "https://example.com/report2024.pdf"
        date = scraper.extract_date(url, "Annual Report 2024")
        assert date == "2024-01-01"
    
    def test_extract_date_no_date_found(self, scraper):
        """Test when no date is found."""
        url = "https://example.com/report.pdf"
        date = scraper.extract_date(url, "Report")
        assert date is None


class TestURLScraping:
    """Test URL scraping functionality."""
    
    @patch('scraper.requests.Session.get')
    def test_scrape_url_success(self, mock_get, scraper, sample_html):
        """Test successful URL scraping."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = sample_html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock PDF processing to avoid actual downloads
        with patch.object(scraper, 'process_pdf', return_value={'title': 'Test', 'url': 'test.pdf'}):
            documents = scraper.scrape_url('https://example.com')
        
    
    @patch('scraper.requests.Session.get')
    def test_scrape_url_timeout(self, mock_get, scraper):
        """Test scraping with timeout."""
        # Mock timeout
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        documents = scraper.scrape_url('https://example.com')
        
        # Should return empty list on timeout
        assert documents == []


class TestPDFProcessing:
    """Test PDF download and processing."""
    
    @patch('scraper.requests.Session.get')
    @patch('scraper.PyPDF2.PdfReader')
    def test_process_pdf_success(self, mock_pdf_reader, mock_get, scraper, sample_pdf_content):
        """Test successful PDF processing."""
        # Mock PDF download
        mock_response = Mock()
        mock_response.headers = {'Content-Length': '1024'}
        mock_response.iter_content = Mock(return_value=[sample_pdf_content])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock PDF text extraction
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample PDF content " * 50
        mock_pdf_reader.return_value.pages = [mock_page]
        
        pdf_info = {
            'url': 'https://example.com/test.pdf',
            'title': 'Test Document'
        }
        
        document = scraper.process_pdf(pdf_info, 'https://example.com')
        
        # Verify document structure
        assert document is not None
        assert document['title'] == 'Test Document'
        assert document['url'] == 'https://example.com/test.pdf'
        assert document['size_kb'] == 1.0
        assert 'content_preview' in document
        assert 'scraped_at' in document
    
    @patch('scraper.requests.Session.get')
    def test_process_pdf_download_error(self, mock_get, scraper):
        """Test PDF processing with download error."""
        # Mock download error
        mock_get.side_effect = requests.HTTPError("404 Not Found")
        
        pdf_info = {
            'url': 'https://example.com/test.pdf',
            'title': 'Test Document'
        }
        
        document = scraper.process_pdf(pdf_info, 'https://example.com')
        
        # Should return None on error
        assert document is None


class TestPDFTextExtraction:
    """Test PDF text extraction."""
    
    @patch('scraper.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open)
    def test_extract_pdf_text(self, mock_file, mock_pdf_reader, scraper):
        """Test extracting text from PDF."""
        # Mock PDF with text
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample text " * 100
        mock_pdf_reader.return_value.pages = [mock_page]
        
        text = scraper.extract_pdf_text('test.pdf')
        
        # Should return first 500 characters
        assert len(text) <= 500
        assert 'Sample text' in text
    
    @patch('scraper.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=mock_open)
    def test_extract_pdf_text_error(self, mock_file, mock_pdf_reader, scraper):
        """Test text extraction with error."""
        # Mock PDF reading error
        mock_pdf_reader.side_effect = Exception("Invalid PDF")
        
        text = scraper.extract_pdf_text('test.pdf')
        
        # Should return empty string on error
        assert text == ""


class TestDataSaving:
    """Test saving results to JSON."""
    
    def test_save_results(self, scraper, tmp_path):
        """Test saving documents to JSON file."""
        documents = [
            {
                'title': 'Test Document 1',
                'url': 'https://example.com/doc1.pdf',
                'size_kb': 100.5,
                'date_published': '2024-01-15',
                'content_preview': 'Preview text...',
                'scraped_at': '2024-11-25T20:00:00'
            },
            {
                'title': 'Test Document 2',
                'url': 'https://example.com/doc2.pdf',
                'size_kb': 200.0,
                'date_published': None,
                'content_preview': 'Another preview...',
                'scraped_at': '2024-11-25T20:01:00'
            }
        ]
        
        output_file = tmp_path / "test_output.json"
        scraper.save_results(documents, str(output_file))
        
        # Verify file exists
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert 'documents' in data
        assert len(data['documents']) == 2
        assert data['documents'][0]['title'] == 'Test Document 1'


class TestURLLoading:
    """Test loading URLs from file."""
    
    def test_load_urls_from_file(self, tmp_path):
        """Test loading URLs from text file."""
        # Create test file
        url_file = tmp_path / "urls.txt"
        url_file.write_text("""# Comment line
https://example.com/page1

https://example.com/page2
# Another comment
https://example.com/page3
""")
        
        urls = load_urls_from_file(str(url_file))
        
        # Should load 3 URLs, skipping comments and empty lines
        assert len(urls) == 3
        assert 'https://example.com/page1' in urls
        assert 'https://example.com/page2' in urls
        assert 'https://example.com/page3' in urls
    
    def test_load_urls_file_not_found(self):
        """Test loading from non-existent file."""
        urls = load_urls_from_file('nonexistent.txt')
        assert urls == []


class TestSeleniumFunctionality:
    """Test Selenium fallback functionality for 403 errors."""
    
    @patch('scraper.requests.Session.get')
    @patch('scraper.SELENIUM_AVAILABLE', True)
    def test_403_triggers_selenium_fallback(self, mock_get, scraper):
        """Test that 403 error triggers Selenium fallback."""
        # Mock 403 error
        mock_response = Mock()
        mock_response.status_code = 403
        http_error = requests.HTTPError("403 Forbidden")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        
        # Mock Selenium scraping
        with patch.object(scraper, 'scrape_url_with_selenium', return_value=[{'title': 'Test', 'url': 'test.pdf'}]) as mock_selenium:
            documents = scraper.scrape_url('https://example.com')
            
            # Verify Selenium was called
            mock_selenium.assert_called_once_with('https://example.com')
            assert len(documents) == 1
    
    @patch('scraper.requests.Session.get')
    @patch('scraper.SELENIUM_AVAILABLE', False)
    def test_403_without_selenium_available(self, mock_get, scraper):
        """Test 403 error when Selenium is not available."""
        # Mock 403 error
        mock_response = Mock()
        mock_response.status_code = 403
        http_error = requests.HTTPError("403 Forbidden")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        
        documents = scraper.scrape_url('https://example.com')
        
        # Should return empty list when Selenium not available
        assert documents == []
    
    @patch('scraper.SELENIUM_AVAILABLE', True)
    @patch('scraper.uc.Chrome')
    def test_selenium_driver_initialization(self, mock_chrome, scraper, sample_html):
        """Test Selenium driver initialization."""
        # Mock driver
        mock_driver = Mock()
        mock_driver.page_source = sample_html
        mock_chrome.return_value = mock_driver
        
        # Mock PDF processing
        with patch.object(scraper, 'process_pdf', return_value={'title': 'Test', 'url': 'test.pdf'}):
            documents = scraper.scrape_url_with_selenium('https://example.com')
        
        # Verify driver was initialized
        mock_chrome.assert_called_once()
        assert scraper.driver is not None
    
    @patch('scraper.SELENIUM_AVAILABLE', True)
    @patch('scraper.uc.Chrome')
    def test_selenium_scrapes_page(self, mock_chrome, scraper, sample_html):
        """Test Selenium successfully scrapes page."""
        # Mock driver
        mock_driver = Mock()
        mock_driver.page_source = sample_html
        mock_chrome.return_value = mock_driver
        
        # Mock PDF processing
        with patch.object(scraper, 'process_pdf', return_value={'title': 'Test Doc', 'url': 'https://example.com/test.pdf'}):
            documents = scraper.scrape_url_with_selenium('https://example.com')
        
        # Verify driver navigated to URL
        mock_driver.get.assert_called_once_with('https://example.com')
        
        # Verify documents were found
        assert len(documents) > 0
    
    @patch('scraper.SELENIUM_AVAILABLE', True)
    @patch('scraper.uc.Chrome')
    def test_selenium_extracts_pdfs(self, mock_chrome, scraper, sample_html):
        """Test Selenium extracts PDF links from rendered page."""
        # Mock driver
        mock_driver = Mock()
        mock_driver.page_source = sample_html
        mock_chrome.return_value = mock_driver
        
        # Mock PDF processing
        with patch.object(scraper, 'process_pdf', return_value={'title': 'Test', 'url': 'test.pdf'}):
            documents = scraper.scrape_url_with_selenium('https://example.com')
        
        # Should find PDFs from sample_html (has 3 PDF links, but max_pdfs=2 in fixture)
        assert len(documents) <= scraper.max_pdfs
    
    @patch('scraper.SELENIUM_AVAILABLE', True)
    @patch('scraper.uc.Chrome')
    def test_selenium_no_pdfs_found(self, mock_chrome, scraper):
        """Test Selenium when no PDFs are found."""
        # Mock driver with HTML containing no PDFs
        mock_driver = Mock()
        mock_driver.page_source = "<html><body><a href='/page.html'>Link</a></body></html>"
        mock_chrome.return_value = mock_driver
        
        documents = scraper.scrape_url_with_selenium('https://example.com')
        
        # Should return empty list
        assert documents == []
    
    @patch('scraper.SELENIUM_AVAILABLE', True)
    @patch('scraper.uc.Chrome')
    def test_selenium_error_handling(self, mock_chrome, scraper):
        """Test Selenium handles errors gracefully."""
        # Mock driver that raises error
        mock_chrome.side_effect = Exception("Chrome driver failed")
        
        documents = scraper.scrape_url_with_selenium('https://example.com')
        
        # Should return empty list on error
        assert documents == []
    
    @patch('scraper.SELENIUM_AVAILABLE', True)
    def test_selenium_driver_reuse(self, scraper):
        """Test that Selenium driver is reused across calls."""
        # Mock driver
        mock_driver = Mock()
        scraper.driver = mock_driver
        
        with patch('scraper.uc.Chrome') as mock_chrome:
            # Call twice
            with patch.object(scraper, 'extract_pdf_links', return_value=[]):
                scraper.scrape_url_with_selenium('https://example.com')
                scraper.scrape_url_with_selenium('https://example.com')
            
            # Chrome should not be initialized again (driver already exists)
            mock_chrome.assert_not_called()
    
    def test_selenium_driver_cleanup(self, scraper):
        """Test Selenium driver cleanup on deletion."""
        # Mock driver
        mock_driver = Mock()
        scraper.driver = mock_driver
        
        # Trigger cleanup
        scraper.close()
        
        # Verify driver.quit() was called
        mock_driver.quit.assert_called_once()


class TestURLDecoding:
    """Test URL-encoded filename handling."""
    
    @patch('scraper.requests.Session.get')
    @patch('scraper.PyPDF2.PdfReader')
    def test_url_encoded_filename_decoded(self, mock_pdf_reader, mock_get, scraper):
        """Test that URL-encoded filenames are properly decoded."""
        # Mock PDF download with URL-encoded filename
        mock_response = Mock()
        mock_response.headers = {'Content-Length': '1024'}
        mock_response.iter_content = Mock(return_value=[b'PDF content'])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock PDF text extraction
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample text"
        mock_pdf_reader.return_value.pages = [mock_page]
        
        # URL with Cyrillic characters (URL-encoded)
        pdf_info = {
            'url': 'https://example.com/%D0%97%D0%B0%D0%BA%D0%BE%D0%BD.pdf',
            'title': 'Test'
        }
        
        document = scraper.process_pdf(pdf_info, 'https://example.com')
        
        # Verify document was processed (filename was decoded successfully)
        assert document is not None
        assert document['url'] == pdf_info['url']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

