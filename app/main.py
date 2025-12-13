"""
Multi-Agent Study Assistant - Main Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

from app.models.session import create_db_and_tables
from app.routers import plans, schedule, knowledge, chat
from app.config import BASE_DIR, UPLOAD_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - setup and teardown."""
    # Startup
    print("🚀 Starting Study Assistant...")
    
    # Create database tables
    create_db_and_tables()
    print("✅ Database initialized")
    
    # Create upload directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print("✅ Upload directory ready")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Study Assistant...")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Study Assistant",
    description="AI-powered study planning and doubt resolution system",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routers
app.include_router(plans.router)
app.include_router(schedule.router)
app.include_router(knowledge.router)
app.include_router(chat.router)

# Setup templates
templates_dir = BASE_DIR / "frontend" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Frontend routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page / Dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/plan", response_class=HTMLResponse)
async def plan_page(request: Request):
    """Create study plan page."""
    return templates.TemplateResponse("plan.html", {"request": request})


@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    """Today's tasks page."""
    return templates.TemplateResponse("schedule.html", {"request": request})


@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    """Notes and doubts page."""
    return templates.TemplateResponse("knowledge.html", {"request": request})


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "study-assistant"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
