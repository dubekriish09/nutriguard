from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./nutriguard.db"
    
    JWT_SECRET: str = "dev-secret-do-not-use-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    GEMINI_API_KEY: Optional[str] = None
    
    DEBUG: bool = False  # Added DEBUG flag for development/demo mode
    
    CORS_ORIGINS: List[str] = ["*"]
    RATE_LIMIT_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
