"""
Main entry point for the Web Scraper application.
Serves both the FastAPI backend and static frontend.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from scrape_service import app as scrape_app


# Mount the scraper API
app = FastAPI(
    title="Web Scraper",
    description="Full-stack web scraping application",
    version="1.0.0"
)

# Include scrape service routes
app.mount("/api", scrape_app)

# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent

# Serve static files
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend not found. API available at /api/"}


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon to prevent 404 logs."""
    from fastapi.responses import Response
    # Return a simple 1x1 transparent PNG
    transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=transparent_png, media_type="image/png")


@app.get("/health")
async def health():
    """Health check for the main app."""
    return {"status": "healthy", "service": "web-scraper"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )