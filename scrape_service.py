"""
Web Scraper API Service
FastAPI backend that exposes scraping functionality via REST API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import re
import os

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

# Output directory for saved files
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


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


class SaveRequest(BaseModel):
    """Request model for save endpoint."""
    content: str
    filename: str
    format: str = "md"  # md or txt
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Sanitize filename."""
        # Remove invalid characters
        v = re.sub(r'[<>:"/\\|?*]', '', v)
        v = v.strip()
        if not v:
            v = "scraped_content"
        return v[:100]  # Limit length


class ScrapeResponse(BaseModel):
    """Response model for scraping endpoint."""
    success: bool
    title: str
    url: str
    markdown: str
    text: str
    error: Optional[str] = None


class SaveResponse(BaseModel):
    """Response model for save endpoint."""
    success: bool
    filepath: str
    filename: str
    message: str


class FileInfo(BaseModel):
    """File information model."""
    name: str
    path: str
    size: int
    modified: str


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


@app.post("/save", response_model=SaveResponse)
async def save_endpoint(request: SaveRequest):
    """
    Save scraped content to the outputs directory.
    
    Args:
        request: SaveRequest containing content, filename, and format
        
    Returns:
        SaveResponse with filepath and success status
    """
    try:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "md" if request.format == "md" else "txt"
        filename = f"{request.filename}_{timestamp}.{extension}"
        
        filepath = OUTPUT_DIR / filename
        
        # Write content to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        return SaveResponse(
            success=True,
            filepath=str(filepath),
            filename=filename,
            message=f"File saved successfully to outputs/{filename}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )


@app.get("/files", response_model=List[FileInfo])
async def list_files():
    """
    List all saved files in the outputs directory.
    
    Returns:
        List of FileInfo objects
    """
    try:
        files = []
        for file_path in OUTPUT_DIR.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append(FileInfo(
                    name=file_path.name,
                    path=str(file_path),
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                ))
        
        # Sort by modified date (newest first)
        files.sort(key=lambda x: x.modified, reverse=True)
        return files
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )


@app.get("/files/{filename}")
async def download_file(filename: str):
    """
    Download a saved file.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        FileResponse with the file content
    """
    filepath = OUTPUT_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not filepath.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    
    # Security check - ensure file is within outputs directory
    try:
        filepath.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="text/plain"
    )


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    Delete a saved file.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        Success message
    """
    filepath = OUTPUT_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check
    try:
        filepath.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        filepath.unlink()
        return {"success": True, "message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)