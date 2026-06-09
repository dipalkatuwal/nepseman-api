from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NEPSE_BASE_URL: str = "https://www.nepalstock.com"
    NEPSE_VERIFY_SSL: bool = False
    LOG_LEVEL: str = "INFO"

    # Cache TTL in seconds (default 10 min for stable data, 30s for live)
    CACHE_TTL_DEFAULT: int = 600
    CACHE_TTL_LIVE: int = 30

    # Rate limiting (requests per minute per IP)
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_LIVE: str = "120/minute"
    RATE_LIMIT_HEALTH: str = "200/minute"

    DATABASE_URL: str = "postgresql+asyncpg://nepse:nepse@localhost:5432/nepse_db"
    
    class Config:
        env_file = ".env"


settings = Settings()
