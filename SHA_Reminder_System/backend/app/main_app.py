"""
Application entry point that serves the user-facing HTML app at root.
"""
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

def mount_frontend(app):
    """
    Mount the frontend static files and serve index.html at root.
    """
    frontend_path = Path(__file__).parent.parent.parent / "frontend"
    frontend_path.mkdir(exist_ok=True)

    @app.get("/", include_in_schema=False)
    async def serve_app():
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend not built yet"}

    # Serve static files (CSS, JS, images) if needed
    static_path = frontend_path / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
