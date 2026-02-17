"""Configuration management for Space Money backend."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://anshmarwa@localhost:5432/space_money"
    
    # Lean Technologies
    lean_app_token: str = ""
    lean_client_id: str = "33429486-4597-4dbf-b122-2ac4920d8f1d"
    lean_client_secret: str = "33333432393438362d343539372d3464"
    lean_auth_url: str = "https://auth.sandbox.leantech.me"
    lean_base_url: str = "https://sandbox.leantech.me"
    
    # AWS S3
    aws_region: str = "me-central-1"
    aws_access_key_id: str = "dummy"
    aws_secret_access_key: str = "dummy"
    s3_bucket_name: str = "space-money-dev"
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # DIFC Compliance - Field-level encryption
    encryption_key: str = ""  # AES-256 key for PII encryption
    
    # Application
    environment: str = "development"
    # Make data_dir relative to this file (backend/data)
    data_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    
    model_config = SettingsConfigDict(
        # Look for .env in the same directory as this file
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
