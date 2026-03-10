"""ERP Emulator Service - Main Application

Standalone ERP emulator service for testing and development.
Runs on port 6688 with separate SQLite database.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db, engine
from api import suppliers, materials, orders, payments, contracts, admin
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting ERP Emulator Service...")
    logger.info(f"Database: {settings.DATABASE_URL}")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down ERP Emulator Service...")
    await engine.dispose()
    logger.info("Database connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Standalone ERP emulator for testing and development",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(suppliers.router)
app.include_router(materials.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(contracts.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "suppliers": "/api/suppliers",
            "materials": "/api/materials",
            "orders": "/api/orders",
            "payments": "/api/payments",
            "contracts": "/api/contracts",
            "admin": "/api/admin",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
