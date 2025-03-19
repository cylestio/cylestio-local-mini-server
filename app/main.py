from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.database.init_db import init_db
from app.routers import agents, events
from app.routers.metrics import router as metrics_router
from app.routers.telemetry import router as telemetry_router
from app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the FastAPI application."""
    # Startup
    await init_db()
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(
    title="Cylestio Mini-Local Server",
    description="A lightweight server for collecting and querying Cylestio monitoring data",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - in production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
app.include_router(telemetry_router, prefix="/api", tags=["telemetry"])
app.include_router(api_router, prefix="/api", tags=["api"])

@app.get("/", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "cylestio-mini-local-server"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 