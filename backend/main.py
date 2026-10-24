"""
sha-pay - Main Entry Point
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
import mimetypes
mimetypes.add_type("application/manifest+json", ".webmanifest")

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.router import api_router


def validate_security_settings():
    """Validate security-critical settings at startup."""
    if not settings.SECRET_KEY and not settings.ALLOW_INSECURE_DEFAULTS:
        raise RuntimeError(
            "SECRET_KEY is not set. Set SECRET_KEY in your environment "
            "or .env file before starting the application."
        )
    if not settings.ALLOW_INSECURE_DEFAULTS and (
        len(settings.SECRET_KEY) < 32
        or settings.SECRET_KEY.startswith("change-this")
    ):
        raise RuntimeError(
            "SECRET_KEY is too short or still the example placeholder; "
            "use a random value of at least 32 characters."
        )
    if not settings.ALLOW_INSECURE_DEFAULTS and not settings.MPESA_CALLBACK_SECRET:
        logger.warning(
            "MPESA_CALLBACK_SECRET is not set: M-Pesa callbacks will be rejected."
        )


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
    validate_security_settings()
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
# allow_origins comes from CORS_ORIGINS (localhost ports plus the Vercel deploy).
# Credentials are allowed, so the list must stay explicit: "/*" with
# credentials is rejected by browsers. Cookies are not used (the PWA sends a
# bearer token), but keeping the explicit list costs nothing.
cors_origins = settings.CORS_ORIGINS or []
if settings.DEBUG:
    cors_origins = list(cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routes under /api
app.include_router(api_router)

# Serve the HTML app at root (both "/" and "/index.html" since the service
# worker pre-caches "/index.html" explicitly in its APP_SHELL list).
@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def serve_app():
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "sha-pay - Frontend not found. Open frontend/index.html directly."}


# PWA support: service worker, manifest, and app icons.
# The service worker MUST be served at the top-level scope ("/") so it can
# intercept requests for the whole app (sub-path SWs cannot control "/").
@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    sw_file = frontend_path / "sw.js"
    if sw_file.exists():
        return FileResponse(str(sw_file), media_type="application/javascript")
    return {"message": "Service worker not found"}


@app.get("/manifest.webmanifest", include_in_schema=False)
async def serve_manifest():
    manifest_file = frontend_path / "manifest.webmanifest"
    if manifest_file.exists():
        return FileResponse(str(manifest_file), media_type="application/manifest+json")
    return {"message": "Manifest not found"}


# Serve static assets if they exist
static_path = frontend_path / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Serve PWA icons directory if it exists
icons_path = frontend_path / "icons"
if icons_path.exists():
    app.mount(
        "/icons",
        StaticFiles(directory=str(icons_path)),
        name="icons",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )