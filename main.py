from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.database import test_connection
from routes.ai_routes import router as ai_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    print("🚀 Starting CRM AI Backend...")
    if test_connection():
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
    
    yield  # This is where the app runs
    
    # Shutdown (if you need cleanup later)
    print("👋 Shutting down CRM AI Backend...")

app = FastAPI(
    title="CRM AI Backend",
    description="AI-powered queries for CRM data", 
    version="1.0.0",
    lifespan=lifespan  # Use the new lifespan instead of on_event
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ai_router)

@app.get("/")
async def root():
    return {"message": "CRM AI Backend is running!"}

@app.get("/health")
async def health():
    db_status = test_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)