import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import STORAGE_DIR
from init_db import init_database
from routers.auth import router as auth_router
from routers.roster import router as roster_router
from routers.tasks import router as tasks_router
from routers.submissions import router as submissions_router, admin_submissions_router
from routers.model_config import router as model_config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Path(STORAGE_DIR).joinpath("submissions").mkdir(parents=True, exist_ok=True)
    init_database()
    yield


app = FastAPI(title="AI Homework Grading Platform", lifespan=lifespan, docs_url=None, redoc_url=None)

# Register API routers (must come before static file mount)
app.include_router(auth_router)
app.include_router(roster_router)
app.include_router(tasks_router)
app.include_router(submissions_router)
app.include_router(admin_submissions_router)
app.include_router(model_config_router)

# Mount frontend static files
dist_path = Path(__file__).resolve().parent / "dist"
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Serve static files if they exist, otherwise return index.html for SPA routing
        file_path = dist_path / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")
