"""
Web Scraper API Service
FastAPI backend that exposes scraping functionality via REST API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
import re

from scraper import WebScraper, scrape_url


app = FastAPI(
    title="Web Scraper API",
    description="A REST API for scraping web pages and converting them to structured markdown",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    """Request model for scraping endpoint."""
    url: str
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate and normalize the URL."""
        v = v.strip()
        
        # Add https:// if no protocol specified
        if not re.match(r'^https?://', v, re.IGNORECASE):
            v = 'https://' + v
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('Invalid URL format')
        
        return v


class ScrapeResponse(BaseModel):
    """Response model for scraping endpoint."""
    success: bool
    title: str
    url: str
    markdown: str
    text: str
    error: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "Web Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/scrape": "POST - Scrape a URL and return markdown content",
            "/health": "GET - Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):
    """
    Scrape a URL and return the content as structured markdown.
    
    Args:
        request: ScrapeRequest containing the URL to scrape
        
    Returns:
        ScrapeResponse with title, markdown content, and plain text
    """
    try:
        result = scrape_url(request.url)
        
        return ScrapeResponse(
            success=True,
            title=result['title'],
            url=result['url'],
            markdown=result['markdown'],
            text=result['text']
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        error_message = str(e)
        
        # Provide more specific error messages
        if "Failed to fetch URL" in error_message:
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch the URL: {error_message}"
            )
        
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while scraping: {error_message}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
