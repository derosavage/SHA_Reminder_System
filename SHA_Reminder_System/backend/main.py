"""
SHA Reminder & Penalty Estimation System - Main Entry Point
Serves the user-facing HTML app at root, API at /api/v1
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import sys
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.router import api_router


def configure_logging():
    """Configure application logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        level="INFO" if not settings.DEBUG else "DEBUG",
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
    )
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    configure_logging()
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
        logger.info("App will start without database (some features may be limited)")

    yield

    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


# Determine frontend path
frontend_path = Path(__file__).parent / "frontend"
if not frontend_path.exists():
    frontend_path = Path(__file__).parent.parent / "frontend"

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=None,      # Hide Swagger docs from users
    redoc_url=None,      # Hide ReDoc from users
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routes under /api
app.include_router(api_router)

# Serve the HTML app at root
@app.get("/", include_in_schema=False)
async def serve_app():
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "SHA Reminder System - Frontend not found. Open frontend/index.html directly."}

# Serve static assets if they exist
static_path = frontend_path / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )