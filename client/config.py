"""
Client configuration settings.
"""

import os
from dataclasses import dataclass


@dataclass
class ClientSettings:
    """Client configuration."""
    
    # Server connection
    server_host: str = "localhost"
    server_port: int = 8765
    
    # Reconnection settings
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    
    # UI settings
    window_width: int = 1280
    window_height: int = 800
    
    @property
    def server_url(self) -> str:
        return f"ws://{self.server_host}:{self.server_port}"


def load_settings() -> ClientSettings:
    """Load settings from environment variables."""
    return ClientSettings(
        server_host=os.getenv("MONOPOLY_SERVER_HOST", "localhost"),
        server_port=int(os.getenv("MONOPOLY_SERVER_PORT", "8765")),
        reconnect_attempts=int(os.getenv("MONOPOLY_RECONNECT_ATTEMPTS", "5")),
        reconnect_delay=float(os.getenv("MONOPOLY_RECONNECT_DELAY", "2.0")),
        window_width=int(os.getenv("MONOPOLY_WINDOW_WIDTH", "1280")),
        window_height=int(os.getenv("MONOPOLY_WINDOW_HEIGHT", "800")),
    )


settings = load_settings()
