"""
Main FastAPI application for the law-firm case management platform.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database import engine, Base, SessionLocal
from .seed import seed_if_empty
from .core.security import get_current_active_user
from .routers import cases, lawyers, clients, opposing_parties, evidence, auth, analytics
try:
    from app.routers import ai_analytics
    AI_ROUTER_AVAILABLE = True
except Exception as e:  # ML deps (sklearn/xgboost/prophet) are optional
    ai_analytics = None
    AI_ROUTER_AVAILABLE = False
    print(f"AI analytics router disabled (optional ML deps missing): {e}")
# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on application startup/shutdown (replaces deprecated @app.on_event)"""
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("API documentation: http://localhost:8000/docs")
    print(f"Debug mode: {settings.DEBUG}")
    yield
    print("Shutting down Law Firm Case Management API")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="REST API for one litigation firm's matters, counsel, clients, and evidence files.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Law Firm Case Management API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }

# Include routers
API_V1_PREFIX = "/api/v1"

# Every router below except /auth needs a logged-in, active user.
# /auth sets its own rules: login is public, user management is admin-only.
protected = [Depends(get_current_active_user)]

app.include_router(
    auth.router,
    prefix=f"{API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    cases.router,
    prefix=f"{API_V1_PREFIX}/cases",
    tags=["Matters"],
    dependencies=protected,
)

app.include_router(
    cases.courts_router,
    prefix=f"{API_V1_PREFIX}/courts",
    tags=["Courts"],
    dependencies=protected,
)

app.include_router(
    lawyers.router,
    prefix=f"{API_V1_PREFIX}/lawyers",
    tags=["Lawyers"],
    dependencies=protected,
)

app.include_router(
    lawyers.groups_router,
    prefix=f"{API_V1_PREFIX}/practice-groups",
    tags=["Practice groups"],
    dependencies=protected,
)

app.include_router(
    opposing_parties.router,
    prefix=f"{API_V1_PREFIX}/opposing-parties",
    tags=["Opposing parties"],
    dependencies=protected,
)

app.include_router(
    clients.router,
    prefix=f"{API_V1_PREFIX}/clients",
    tags=["Clients"],
    dependencies=protected,
)

app.include_router(
    evidence.router,
    prefix=f"{API_V1_PREFIX}/evidence",
    tags=["Evidence"],
    dependencies=protected,
)

app.include_router(
    analytics.router,
    prefix=f"{API_V1_PREFIX}/analytics",
    tags=["Analytics"],
    dependencies=protected,
)
if AI_ROUTER_AVAILABLE:
    app.include_router(ai_analytics.router, dependencies=protected)