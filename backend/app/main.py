"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="APISEC v1",
    description="Automated OpenAPI Documentation Generator",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    # Common React dev server origins (support both localhost and 127.0.0.1)
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "APISEC v1",
        "description": "Automated OpenAPI Documentation Generator",
        "version": "1.0.0",
        "endpoints": {
            "generate": "/api/generate",
            "reports": "/api/reports",
            "download_report": "/api/reports/{report_id}"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
