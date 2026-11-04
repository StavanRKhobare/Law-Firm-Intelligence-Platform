"""
Configuration settings for the law-firm case management API
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    APP_NAME: str = "Law Firm Case Management API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # Fill an empty SQLite database with the sample firm. PostgreSQL uses database/sample_data.sql.
    SEED_SAMPLE_DATA: bool = False
    
    DATABASE_URL: str
    
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "law_firm_documents"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    MAX_FILE_SIZE: int = 52428800
    ALLOWED_FILE_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "application/pdf",
        "image/tiff",
        "video/mp4",
        "audio/mpeg",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]
    UPLOAD_DIR: str = "./uploads"
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()