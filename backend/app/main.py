import logging
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database.session import engine, Base, run_migrations
import app.database.models  # Register models with Base
from app.api.health import router as health_router
from app.api.examinations import router as examinations_router
from app.api.demo import router as demo_router

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("satya")

# Initialize database schema and run migrations
Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(
    title=settings.PROJECT_FULL_NAME,
    description="""
## SCSS-SATYA V3 — Forensic-Led Digital Image Authenticity Screening Platform
Developed for **Sure Clue Scientific Solutions (SCSS)**.

### Core Guiding Doctrine:
> **"The tool screens. The evidence speaks. The expert decides."**
> Automated findings are never presented as conclusive forensic opinions, legal proof,
> or definitive proof that an image is authentic or manipulated.

### Defensible 4-Layer Architecture:
1. **Passive-Blind Screening**: Technical indicators across metadata, ELA, and sensor/image consistency.
2. **Cryptographic Integrity**: SHA-256 evidence integrity hashing and bitstream preservation.
3. **Explainable Findings**: Transparent indicators, explanations, limitations, and manual review steps.
4. **Qualified Human Review**: Formal examiner attestation and verifiable ISO/IEC 27037 PDF reports.
    """,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Prevents sensitive internal stack traces and filesystem paths from leaking to clients.
    """
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An error occurred while processing the forensic request. The event has been logged.",
            "disclaimer": settings.MANDATORY_DISCLAIMER,
        },
    )


# Register API routers
app.include_router(health_router, prefix="/api")
app.include_router(examinations_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


# Optional: Mount frontend build if built into frontend/dist
frontend_dist = settings.ROOT_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"status": "Frontend build not mounted."})
