"""
Data models for database operations.

These are simple dataclasses that map to database rows,
separate from the game engine models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GameRecord:
    """Database representation of a game."""
    id: str
    name: str
    status: str = "waiting"
    current_player_index: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
    winner_id: str | None = None
    settings_json: str = "{}"
    
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "GameRecord":
        """Create from database row."""
        return cls(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            current_player_index=row["current_player_index"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            finished_at=row["finished_at"],
            winner_id=row["winner_id"],
            settings_json=row["settings_json"]
        )


@dataclass
class PlayerRecord:
    """Database representation of a player."""
    id: str
    game_id: str
    name: str
    token: str
    turn_order: int
    position: int = 0
    money: int = 1500
    is_bankrupt: bool = False
    is_in_jail: bool = False
    jail_turns: int = 0
    get_out_of_jail_cards: int = 0
    connected: bool = False
    created_at: datetime | None = None
    
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PlayerRecord":
        """Create from database row."""
        return cls(
            id=row["id"],
            game_id=row["game_id"],
            name=row["name"],
            token=row["token"],
            turn_order=row["turn_order"],
            position=row["position"],
            money=row["money"],
            is_bankrupt=bool(row["is_bankrupt"]),
            is_in_jail=bool(row["is_in_jail"]),
            jail_turns=row["jail_turns"],
            get_out_of_jail_cards=row["get_out_of_jail_cards"],
            connected=bool(row["connected"]),
            created_at=row["created_at"]
        )


@dataclass
class PropertyRecord:
    """Database representation of property ownership."""
    game_id: str
    position: int
    owner_id: str | None = None
    houses: int = 0
    is_mortgaged: bool = False
    
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PropertyRecord":
        """Create from database row."""
        return cls(
            game_id=row["game_id"],
            position=row["position"],
            owner_id=row["owner_id"],
            houses=row["houses"],
            is_mortgaged=bool(row["is_mortgaged"])
        )


@dataclass
class GameStateSnapshot:
    """
    Complete serialized game state for recovery.
    
    This stores the full JSON from game.to_dict() for 
    point-in-time recovery.
    """
    id: int | None
    game_id: str
    state_json: str
    turn_number: int
    created_at: datetime | None = None
    
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "GameStateSnapshot":
        """Create from database row."""
        return cls(
            id=row["id"],
            game_id=row["game_id"],
            state_json=row["state_json"],
            turn_number=row["turn_number"],
            created_at=row["created_at"]
        )


@dataclass
class CardDeckRecord:
    """Database representation of a card deck state."""
    game_id: str
    deck_type: str  # "chance" or "community_chest"
    card_order_json: str
    current_index: int = 0
    
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CardDeckRecord":
        """Create from database row."""
        return cls(
            game_id=row["game_id"],
            deck_type=row["deck_type"],
            card_order_json=row["card_order_json"],
            current_index=row["current_index"]
        )


@dataclass
class GameSummary:
    """Lightweight game info for listings."""
    id: str
    name: str
    status: str
    player_count: int
    created_at: datetime | None
    updated_at: datetime | None
