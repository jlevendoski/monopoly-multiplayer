"""
Server configuration loaded from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Server configuration."""
    
    # Server settings
    HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SERVER_PORT", "8765"))
    SECRET_KEY: str = os.getenv("SERVER_SECRET_KEY", "change-me-in-production")
    
    # Database
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "./data/monopoly.db"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Game settings
    MIN_PLAYERS: int = 2
    MAX_PLAYERS: int = 4
    TURN_TIMEOUT: int = 300  # 5 minutes per turn
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


config = Config()
settings = config  # Alias for backward compatibility
