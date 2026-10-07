import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis.asyncio as aioredis

from app.core.config import settings
from app.db.session import engine
from app.api.v1 import auth, projects, tasks, analyzer, execution, generator

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("astra")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ASTRA — Intelligent Automated Software Testing & Defect Detection Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Basic process liveness probe."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health/ready", status_code=status.HTTP_200_OK, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health/ready", status_code=status.HTTP_200_OK, tags=["Health"])
async def readiness_check():
    """Readiness probe checking PostgreSQL database and Redis connectivity."""
    db_status = False
    redis_status = False

    # 1. Test PostgreSQL DB connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = True
    except Exception as exc:
        logger.error(f"Readiness check failed for PostgreSQL: {exc}")

    # 2. Test Redis connection
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_status = True
    except Exception as exc:
        logger.error(f"Readiness check failed for Redis: {exc}")

    is_ready = db_status and redis_status
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": {
            "database": "online" if db_status else "offline",
            "redis": "online" if redis_status else "offline"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Register V1 API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router, prefix=settings.API_V1_STR)
app.include_router(analyzer.router, prefix=settings.API_V1_STR)
app.include_router(execution.router, prefix=settings.API_V1_STR)
app.include_router(generator.router, prefix=settings.API_V1_STR)
