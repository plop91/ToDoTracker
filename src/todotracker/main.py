"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from todotracker.config import get_settings
from todotracker.database import init_db, close_db, async_session_maker
from todotracker.api import router
from todotracker.services.todo_service import PriorityService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()

    # Seed default priority levels
    async with async_session_maker() as session:
        priority_service = PriorityService(session)
        await priority_service.seed_defaults()
        await session.commit()

    yield

    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="A task manager that lets you spend less time setting up and more time doing",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include API routes
    app.include_router(router)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    # Serve frontend if configured
    frontend_dir = settings.frontend_dir
    if frontend_dir and frontend_dir.exists():
        # Mount static assets (js, css, images)
        static_dir = frontend_dir / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def serve_frontend(request: Request):
            """Serve the frontend application."""
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return HTMLResponse("<h1>ToDoTracker</h1><p>Frontend not found.</p>")

        @app.get("/{path:path}")
        async def serve_frontend_files(path: str):
            """Serve frontend static files or fallback to index.html for SPA routing."""
            # Resolve the path and check it's within the frontend directory
            # This prevents path traversal attacks like /../../../etc/passwd
            try:
                file_path = (frontend_dir / path).resolve()
                frontend_resolved = frontend_dir.resolve()

                # Ensure the resolved path is within the frontend directory
                # is_relative_to() is the safest cross-platform check (Python 3.9+)
                if not file_path.is_relative_to(frontend_resolved):
                    return HTMLResponse("<h1>Forbidden</h1>", status_code=403)

                if file_path.exists() and file_path.is_file():
                    return FileResponse(file_path)
            except (ValueError, OSError):
                # Invalid path (e.g., null bytes, invalid characters)
                return HTMLResponse("<h1>Bad Request</h1>", status_code=400)

            # Fallback to index.html for SPA routing
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return HTMLResponse("<h1>Not Found</h1>", status_code=404)

    return app


app = create_app()


def run_server():
    """Run the API server."""
    settings = get_settings()
    uvicorn.run(
        "todotracker.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run_server()
