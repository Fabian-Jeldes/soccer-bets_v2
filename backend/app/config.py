from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    WS_PORT: int = 8000
    SIMULATION_SPEED_SEC: float = 2.0  # Frecuencia de actualización del simulador
    DATABASE_URL: str = "sqlite+aiosqlite:///./soccer_bets.db"
    
    class Config:
        env_file = ".env"

settings = Settings()

