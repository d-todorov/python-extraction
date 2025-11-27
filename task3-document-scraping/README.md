# Task 3: Document Scraping

Ethical web scraper that extracts PDFs from websites with metadata collection.

## Features

- ✅ PDF link discovery
- ✅ Metadata extraction (title, description, author)
- ✅ Selenium fallback for 403 errors
- ✅ Robots.txt compliance
- ✅ Rate limiting (configurable delay)
- ✅ One-level deep crawling
- ✅ URL decoding for proper filenames
- ✅ Filename length truncation (100 chars max)

## Quick Start

```bash
cd task3-document-scraping
pip install -r requirements.txt
python scraper.py
```

## Configuration

Edit `sample_urls.txt` with URLs to scrape (one per line):
```
https://example.com/page-with-pdfs
https://another-site.com/documents
```

## Output

**Files**:
- `scraped_documents.json` - Metadata for all found PDFs
- `downloads/` - Downloaded PDF files

**JSON Structure**:
```json
{
  "url": "https://example.com",
  "pdfs": [
    {
      "title": "Annual Report 2024",
      "pdf_url": "https://example.com/report.pdf",
      "local_path": "downloads/report.pdf",
      "file_size_bytes": 1234567
    }
  ]
}
```

## Ethical Practices

- ✅ Respects robots.txt
- ✅ 2-second delay between requests
- ✅ Limits to 3 PDFs per site
- ✅ User-Agent identification
- ✅ No aggressive crawling

## How It Works

1. **Main Page**: Scrapes URL for PDF links
2. **Crawl Subpages**: If no PDFs found, checks one level deeper
3. **Selenium Fallback**: Uses browser automation if 403 Forbidden
4. **Download**: Saves PDFs with metadata
5. **Cleanup**: Properly closes browser sessions

## Technologies

- **BeautifulSoup** - HTML parsing
- **Selenium** - Browser automation
- **undetected-chromedriver** - Anti-bot bypass
- **PyPDF2** - PDF text extraction
- **lxml** - Fast XML/HTML parsing

## Testing

```bash
python -m pytest tests.py -v
```

## Troubleshooting

### 403 Forbidden Errors
The scraper automatically uses Selenium with undetected-chromedriver to bypass anti-bot protection.

### Long Filenames
Filenames are automatically truncated to 100 characters to avoid Windows path length issues.

### Chrome Not Found
Install Google Chrome browser, or the script will auto-download ChromeDriver.

## Author

Document Scraping Task  
Date: 2025-11-26
