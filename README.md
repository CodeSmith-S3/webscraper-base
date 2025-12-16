# Web Scraper

A full-stack web scraping application that extracts clean, structured content from any webpage and converts it to markdown format.

## Features

- **Smart Content Extraction**: Automatically identifies and extracts main content from web pages
- **Markdown Conversion**: Preserves HTML structure (headings, lists, tables, code blocks, links, images)
- **Modern UI**: Clean, responsive frontend with live preview
- **REST API**: Simple POST endpoint for programmatic access
- **Docker Ready**: Single command deployment with Docker

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

Then open http://localhost:8001 in your browser.

### Using Docker

```bash
# Build and run with a single command
docker build -t webscraper . && docker run -p 8001:8001 -v ./outputs:/app/outputs webscraper
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Project Structure

```
.
├── main.py              # Main entry point, serves frontend + mounts API
├── scraper.py           # Core scraping logic (BeautifulSoup + requests)
├── scrape_service.py    # FastAPI backend service
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Modern Python packaging
├── Dockerfile           # Container configuration
├── .dockerignore        # Docker build exclusions
├── README.md            # This file
└── static/
    └── index.html       # Frontend UI
```

## API Usage

### Scrape Endpoint

**POST** `/api/scrape`

Request body:
```json
{
    "url": "https://example.com"
}
```

Response:
```json
{
    "success": true,
    "title": "Page Title",
    "url": "https://example.com",
    "markdown": "# Page Title\n\nContent in markdown...",
    "text": "Plain text content..."
}
```

### Example with curl

```bash
curl -X POST http://localhost:8001/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Example with Python

```python
import requests

response = requests.post(
    "http://localhost:8001/api/scrape",
    json={"url": "https://example.com"}
)

data = response.json()
print(data["markdown"])
```

## Using the Scraper Module Directly

```python
from scraper import scrape_url, WebScraper

# Quick scrape
result = scrape_url("https://example.com")
print(result["markdown"])

# With custom settings
scraper = WebScraper(timeout=60)
result = scraper.scrape("https://example.com")
```

## Supported Content Conversion

The scraper preserves these HTML elements in markdown:

| HTML Element | Markdown Output |
|-------------|-----------------|
| `<h1>` - `<h6>` | `#` - `######` headings |
| `<p>` | Paragraphs |
| `<a>` | `[text](url)` links |
| `<img>` | `![alt](src)` images |
| `<ul>`, `<ol>` | Bullet/numbered lists |
| `<table>` | Markdown tables |
| `<code>`, `<pre>` | Code blocks |
| `<blockquote>` | `>` quotes |
| `<strong>`, `<b>` | `**bold**` |
| `<em>`, `<i>` | `*italic*` |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8001` | Server port |
| `HOST` | `0.0.0.0` | Server host |

### Scraper Settings

```python
scraper = WebScraper(
    timeout=30  # Request timeout in seconds
)
```

## Health Check

```bash
curl http://localhost:8001/health
# {"status": "healthy", "service": "web-scraper"}
```

## License

MIT License