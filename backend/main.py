from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from database import engine
import models
import os
from dotenv import load_dotenv

load_dotenv()

# Create DB tables
models.Base.metadata.create_all(bind=engine)

# Routers
from routers import users, ideas, forum, dashboard, admin, messages, connections, payments
from routers import ai_routes
from ai_email_agent import start_scheduler

# ── Lifespan: start/stop scheduler with the app ──
@asynccontextmanager
async def lifespan(app):
    scheduler = start_scheduler()
    print("[STARTUP] AI Email Agent scheduler started")
    yield
    scheduler.shutdown(wait=False)
    print("[SHUTDOWN] AI Email Agent scheduler stopped")

app = FastAPI(
    title="StartupSphere API",
    description="Backend API for StartupSphere - Share Startup Ideas Platform",
    version="1.0.0",
    lifespan=lifespan
)

# ── Rate limiting (protects login/signup/forgot-password from abuse) ──
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — only allow requests from approved frontend domains ──
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

# Fallback for local development if ALLOWED_ORIGINS isn't set
if not allowed_origins:
    allowed_origins = ["http://127.0.0.1:5500", "http://localhost:5500"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── STATIC FILES — serve uploaded images (profile avatars, idea covers) ──
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── ROUTERS ──
app.include_router(users.router)
app.include_router(ideas.router)
app.include_router(forum.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(ai_routes.router)
app.include_router(messages.router)
app.include_router(connections.router)
app.include_router(payments.router)


# ── Start AI Email Agent Scheduler on app startup ──
@app.on_event("startup")
async def startup_event():
    start_scheduler()
    print("[STARTUP] AI Email Agent is running!")


# ── ROOT ──
@app.get("/")
def root():
    return {
        "message": "StartupSphere API is running!",
        "docs":    "https://project1-1-ltbk.onrender.com/docs"
    }