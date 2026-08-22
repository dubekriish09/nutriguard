from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import recommendations, nlp, chat, auth, admin
from core.config import settings

app = FastAPI(
    title="NutriGuard AI API",
    description="AI-Powered Personalized Diet & Medication Nutrition System",
    version="1.0.0"
)

# CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from fastapi import Request
from fastapi.responses import JSONResponse
import uuid

from core.logging import logger

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = str(uuid.uuid4())
    logger.error(f"Unhandled exception: {str(exc)}", extra={"request_id": req_id, "endpoint": request.url.path}, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred."
            },
            "request_id": req_id
        }
    )

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["auth"]
)

app.include_router(
    recommendations.router,
    prefix="/api/v1/recommendations",
    tags=["recommendations"]
)

app.include_router(
    nlp.router,
    prefix="/api/v1/nlp",
    tags=["nlp"]
)

app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["chat"]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["admin"]
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/health/ready")
def readiness_check():
    # Attempt DB connection
    try:
        from api.deps import engine
        with engine.connect() as conn:
            pass
        return {"status": "ready", "database": "healthy"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database unavailable")

@app.get("/")
def read_root():
    return {"message": "Welcome to NutriGuard Engine API"}
