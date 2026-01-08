"""
Database connection management and initialization.
"""

import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from server.config import settings


class Database:
    """
    Thread-safe SQLite database manager.
    
    Handles connection pooling and schema initialization.
    """
    
    _local = threading.local()
    _initialized = False
    _init_lock = threading.Lock()
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._ensure_directory()
        self._ensure_schema()
    
    def _ensure_directory(self) -> None:
        """Create database directory if it doesn't exist."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _ensure_schema(self) -> None:
        """Initialize database schema (once per process)."""
        with Database._init_lock:
            if not Database._initialized:
                with self.get_connection() as conn:
                    self._create_tables(conn)
                Database._initialized = True
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get a thread-local database connection.
        
        Usage:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT ...")
        """
        if not hasattr(Database._local, 'connection') or Database._local.connection is None:
            Database._local.connection = self._create_connection()
        
        conn = Database._local.connection
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimal settings."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Use WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode = WAL")
        
        # Return rows as dictionaries
        conn.row_factory = sqlite3.Row
        
        return conn
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables."""
        conn.executescript(SCHEMA_SQL)
    
    def close_connection(self) -> None:
        """Close the current thread's connection."""
        if hasattr(Database._local, 'connection') and Database._local.connection:
            Database._local.connection.close()
            Database._local.connection = None
    
    def reset_database(self) -> None:
        """Drop and recreate all tables. USE WITH CAUTION."""
        with self.get_connection() as conn:
            # Get all table names
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row['name'] for row in cursor.fetchall()]
            
            # Drop all tables
            for table in tables:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            
            # Recreate schema
            self._create_tables(conn)
        
        Database._initialized = True


SCHEMA_SQL = """
-- Games table: stores game metadata
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    current_player_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    winner_id TEXT,
    settings_json TEXT NOT NULL DEFAULT '{}'
);

-- Players table: stores player data per game
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL,
    name TEXT NOT NULL,
    token TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    money INTEGER NOT NULL DEFAULT 1500,
    is_bankrupt INTEGER NOT NULL DEFAULT 0,
    is_in_jail INTEGER NOT NULL DEFAULT 0,
    jail_turns INTEGER NOT NULL DEFAULT 0,
    get_out_of_jail_cards INTEGER NOT NULL DEFAULT 0,
    turn_order INTEGER NOT NULL,
    connected INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

-- Properties table: stores property ownership and development
CREATE TABLE IF NOT EXISTS properties (
    game_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    owner_id TEXT,
    houses INTEGER NOT NULL DEFAULT 0,
    is_mortgaged INTEGER NOT NULL DEFAULT 0,
    
    PRIMARY KEY (game_id, position),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES players(id) ON DELETE SET NULL
);

-- Game states table: stores serialized snapshots for recovery
CREATE TABLE IF NOT EXISTS game_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

-- Card deck states: tracks card positions
CREATE TABLE IF NOT EXISTS card_decks (
    game_id TEXT NOT NULL,
    deck_type TEXT NOT NULL,
    card_order_json TEXT NOT NULL,
    current_index INTEGER NOT NULL DEFAULT 0,
    
    PRIMARY KEY (game_id, deck_type),
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_players_game_id ON players(game_id);
CREATE INDEX IF NOT EXISTS idx_properties_game_id ON properties(game_id);
CREATE INDEX IF NOT EXISTS idx_properties_owner_id ON properties(owner_id);
CREATE INDEX IF NOT EXISTS idx_game_states_game_id ON game_states(game_id);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
"""


# Global database instance
_db: Database | None = None


def get_database() -> Database:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def init_database(db_path: str | None = None) -> Database:
    """Initialize the database with optional custom path."""
    global _db
    # Reset the initialized flag for new database paths
    Database._initialized = False
    _db = Database(db_path)
    return _db
