import asyncio
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# psycopg async 不支持 Windows 默认的 ProactorEventLoop，
# 必须在 uvicorn 创建 event loop 之前切换 policy。
# 配合 uvicorn.run(loop="none") 使用，使 asyncio.run() 走 policy 路径。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import ENV, PORT
from database import engine
from init_db import init_database
from services.cleanup_service import start_cleanup_scheduler, shutdown_cleanup_scheduler
from services.storage import storage_service
from routers.auth import router as auth_router, student_router as student_auth_router
from routers.classes import router as classes_router
from routers.super_admin import router as super_admin_router
from routers.roster import router as roster_router
from routers.tasks import router as tasks_router
from routers.submissions import router as submissions_router, admin_submissions_router
from routers.model_config import router as model_config_router
from routers.sharing import router as sharing_router, admin_sharing_router
from routers.backups import router as backups_router
from routers.invite_codes import router as invite_codes_router
from routers.assistant import router as assistant_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Startup: initializing MinIO homework bucket...")
    await asyncio.to_thread(storage_service.ensure_bucket)
    logger.info("Startup: initializing MinIO backups bucket...")
    from services.backup_service import init_backups_bucket
    await init_backups_bucket()
    logger.info("Startup: initializing database...")
    await init_database()
    start_cleanup_scheduler(engine)
    logger.info("Startup: complete")
    yield
    shutdown_cleanup_scheduler()


_is_dev = ENV != "production"

app = FastAPI(
    title="AI Homework Grading Platform",
    lifespan=lifespan,
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)

# Register API routers (must come before static file mount)
app.include_router(auth_router)
app.include_router(student_auth_router)
app.include_router(classes_router)
app.include_router(super_admin_router)
app.include_router(roster_router)
app.include_router(tasks_router)
app.include_router(submissions_router)
app.include_router(admin_submissions_router)
app.include_router(model_config_router)
app.include_router(sharing_router)
app.include_router(admin_sharing_router)
app.include_router(backups_router)
app.include_router(invite_codes_router)
app.include_router(assistant_router)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, loop="none")
