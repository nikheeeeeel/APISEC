"""Application configuration."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Storage paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    SPECS_DIR: Path = BASE_DIR / "app" / "storage" / "specs"
    REPORTS_DIR: Path = BASE_DIR / "app" / "storage" / "reports"
    
    # Crawler settings
    MAX_CRAWL_DEPTH: int = 3
    MAX_ENDPOINTS: int = 50
    REQUEST_TIMEOUT: int = 10
    RATE_LIMIT_DELAY: float = 0.5  # seconds between requests
    
    # OpenAPI discovery paths
    OPENAPI_PATHS: list[str] = [
        "/openapi.json",
        "/swagger.json",
        "/v3/api-docs",
        "/api-docs",
        "/swagger/v1/swagger.json",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure storage directories exist
settings.SPECS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
