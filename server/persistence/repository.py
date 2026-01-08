"""
Repository layer for game persistence operations.

Handles all database CRUD operations and game state serialization.
"""

import json
from datetime import datetime
from typing import Any

from server.persistence.database import Database, get_database
from server.persistence.models import (
    GameRecord,
    PlayerRecord,
    PropertyRecord,
    GameStateSnapshot,
    CardDeckRecord,
    GameSummary
)


class GameRepository:
    """
    Repository for game persistence operations.
    
    Provides high-level methods for saving and loading games,
    abstracting away the database details.
    """
    
    def __init__(self, database: Database | None = None):
        self.db = database or get_database()
    
    # =========================================================================
    # Game CRUD Operations
    # =========================================================================
    
    def create_game(self, game_record: GameRecord) -> GameRecord:
        """Create a new game record."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO games (id, name, status, current_player_index, settings_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    game_record.id,
                    game_record.name,
                    game_record.status,
                    game_record.current_player_index,
                    game_record.settings_json
                )
            )
        return game_record
    
    def get_game(self, game_id: str) -> GameRecord | None:
        """Get a game by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM games WHERE id = ?",
                (game_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return GameRecord.from_row(dict(row))
            return None
    
    def update_game(self, game_record: GameRecord) -> None:
        """Update an existing game record."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE games 
                SET name = ?,
                    status = ?,
                    current_player_index = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    finished_at = ?,
                    winner_id = ?,
                    settings_json = ?
                WHERE id = ?
                """,
                (
                    game_record.name,
                    game_record.status,
                    game_record.current_player_index,
                    game_record.finished_at,
                    game_record.winner_id,
                    game_record.settings_json,
                    game_record.id
                )
            )
    
    def delete_game(self, game_id: str) -> bool:
        """Delete a game and all related data (cascades)."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM games WHERE id = ?",
                (game_id,)
            )
            return cursor.rowcount > 0
    
    def list_games(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[GameSummary]:
        """List games with optional status filter."""
        with self.db.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """
                    SELECT g.id, g.name, g.status, g.created_at, g.updated_at,
                           COUNT(p.id) as player_count
                    FROM games g
                    LEFT JOIN players p ON g.id = p.game_id
                    WHERE g.status = ?
                    GROUP BY g.id
                    ORDER BY g.updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT g.id, g.name, g.status, g.created_at, g.updated_at,
                           COUNT(p.id) as player_count
                    FROM games g
                    LEFT JOIN players p ON g.id = p.game_id
                    GROUP BY g.id
                    ORDER BY g.updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
            
            return [
                GameSummary(
                    id=row["id"],
                    name=row["name"],
                    status=row["status"],
                    player_count=row["player_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in cursor.fetchall()
            ]
    
    # =========================================================================
    # Player Operations
    # =========================================================================
    
    def add_player(self, player: PlayerRecord) -> PlayerRecord:
        """Add a player to a game."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO players (
                    id, game_id, name, token, position, money,
                    is_bankrupt, is_in_jail, jail_turns,
                    get_out_of_jail_cards, turn_order, connected
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player.id,
                    player.game_id,
                    player.name,
                    player.token,
                    player.position,
                    player.money,
                    int(player.is_bankrupt),
                    int(player.is_in_jail),
                    player.jail_turns,
                    player.get_out_of_jail_cards,
                    player.turn_order,
                    int(player.connected)
                )
            )
        return player
    
    def get_player(self, player_id: str) -> PlayerRecord | None:
        """Get a player by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM players WHERE id = ?",
                (player_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return PlayerRecord.from_row(dict(row))
            return None
    
    def get_players_for_game(self, game_id: str) -> list[PlayerRecord]:
        """Get all players in a game, ordered by turn order."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM players WHERE game_id = ? ORDER BY turn_order",
                (game_id,)
            )
            return [PlayerRecord.from_row(dict(row)) for row in cursor.fetchall()]
    
    def update_player(self, player: PlayerRecord) -> None:
        """Update a player record."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE players
                SET position = ?,
                    money = ?,
                    is_bankrupt = ?,
                    is_in_jail = ?,
                    jail_turns = ?,
                    get_out_of_jail_cards = ?,
                    connected = ?
                WHERE id = ?
                """,
                (
                    player.position,
                    player.money,
                    int(player.is_bankrupt),
                    int(player.is_in_jail),
                    player.jail_turns,
                    player.get_out_of_jail_cards,
                    int(player.connected),
                    player.id
                )
            )
    
    def update_player_connection(self, player_id: str, connected: bool) -> None:
        """Update only the connection status of a player."""
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE players SET connected = ? WHERE id = ?",
                (int(connected), player_id)
            )
    
    # =========================================================================
    # Property Operations
    # =========================================================================
    
    def save_property(self, prop: PropertyRecord) -> None:
        """Save or update a property record."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO properties (game_id, position, owner_id, houses, is_mortgaged)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(game_id, position) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    houses = excluded.houses,
                    is_mortgaged = excluded.is_mortgaged
                """,
                (
                    prop.game_id,
                    prop.position,
                    prop.owner_id,
                    prop.houses,
                    int(prop.is_mortgaged)
                )
            )
    
    def get_properties_for_game(self, game_id: str) -> list[PropertyRecord]:
        """Get all properties with ownership info for a game."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM properties WHERE game_id = ? ORDER BY position",
                (game_id,)
            )
            return [PropertyRecord.from_row(dict(row)) for row in cursor.fetchall()]
    
    def get_properties_for_player(self, player_id: str) -> list[PropertyRecord]:
        """Get all properties owned by a player."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM properties WHERE owner_id = ? ORDER BY position",
                (player_id,)
            )
            return [PropertyRecord.from_row(dict(row)) for row in cursor.fetchall()]
    
    # =========================================================================
    # Game State Snapshots
    # =========================================================================
    
    def save_game_state(self, game_id: str, state: dict[str, Any], turn_number: int) -> int:
        """
        Save a complete game state snapshot.
        
        Returns the snapshot ID.
        """
        state_json = json.dumps(state)
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO game_states (game_id, state_json, turn_number)
                VALUES (?, ?, ?)
                """,
                (game_id, state_json, turn_number)
            )
            return cursor.lastrowid
    
    def get_latest_game_state(self, game_id: str) -> GameStateSnapshot | None:
        """Get the most recent game state snapshot."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM game_states 
                WHERE game_id = ? 
                ORDER BY turn_number DESC, id DESC
                LIMIT 1
                """,
                (game_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return GameStateSnapshot.from_row(dict(row))
            return None
    
    def get_game_state_at_turn(self, game_id: str, turn_number: int) -> GameStateSnapshot | None:
        """Get game state at a specific turn (for replay/undo)."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM game_states 
                WHERE game_id = ? AND turn_number <= ?
                ORDER BY turn_number DESC 
                LIMIT 1
                """,
                (game_id, turn_number)
            )
            row = cursor.fetchone()
            
            if row:
                return GameStateSnapshot.from_row(dict(row))
            return None
    
    def cleanup_old_snapshots(self, game_id: str, keep_count: int = 10) -> int:
        """
        Delete old snapshots, keeping the most recent ones.
        
        Returns the number of deleted snapshots.
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM game_states 
                WHERE game_id = ? AND id NOT IN (
                    SELECT id FROM game_states 
                    WHERE game_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                )
                """,
                (game_id, game_id, keep_count)
            )
            return cursor.rowcount
    
    # =========================================================================
    # Card Deck Operations
    # =========================================================================
    
    def save_card_deck(self, deck: CardDeckRecord) -> None:
        """Save or update a card deck state."""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO card_decks (game_id, deck_type, card_order_json, current_index)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_id, deck_type) DO UPDATE SET
                    card_order_json = excluded.card_order_json,
                    current_index = excluded.current_index
                """,
                (
                    deck.game_id,
                    deck.deck_type,
                    deck.card_order_json,
                    deck.current_index
                )
            )
    
    def get_card_decks(self, game_id: str) -> list[CardDeckRecord]:
        """Get all card deck states for a game."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM card_decks WHERE game_id = ?",
                (game_id,)
            )
            return [CardDeckRecord.from_row(dict(row)) for row in cursor.fetchall()]
    
    # =========================================================================
    # High-Level Save/Load Operations
    # =========================================================================
    
    def save_full_game(
        self,
        game: GameRecord,
        players: list[PlayerRecord],
        properties: list[PropertyRecord],
        card_decks: list[CardDeckRecord],
        state_snapshot: dict[str, Any] | None = None,
        turn_number: int = 0
    ) -> None:
        """
        Save a complete game state in a single transaction.
        
        This is the primary method for persisting game state.
        """
        with self.db.get_connection() as conn:
            # Update game record
            conn.execute(
                """
                INSERT INTO games (id, name, status, current_player_index, 
                                   finished_at, winner_id, settings_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    current_player_index = excluded.current_player_index,
                    updated_at = CURRENT_TIMESTAMP,
                    finished_at = excluded.finished_at,
                    winner_id = excluded.winner_id,
                    settings_json = excluded.settings_json
                """,
                (
                    game.id,
                    game.name,
                    game.status,
                    game.current_player_index,
                    game.finished_at,
                    game.winner_id,
                    game.settings_json
                )
            )
            
            # Update players
            for player in players:
                conn.execute(
                    """
                    INSERT INTO players (
                        id, game_id, name, token, position, money,
                        is_bankrupt, is_in_jail, jail_turns,
                        get_out_of_jail_cards, turn_order, connected
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        position = excluded.position,
                        money = excluded.money,
                        is_bankrupt = excluded.is_bankrupt,
                        is_in_jail = excluded.is_in_jail,
                        jail_turns = excluded.jail_turns,
                        get_out_of_jail_cards = excluded.get_out_of_jail_cards,
                        connected = excluded.connected
                    """,
                    (
                        player.id,
                        player.game_id,
                        player.name,
                        player.token,
                        player.position,
                        player.money,
                        int(player.is_bankrupt),
                        int(player.is_in_jail),
                        player.jail_turns,
                        player.get_out_of_jail_cards,
                        player.turn_order,
                        int(player.connected)
                    )
                )
            
            # Update properties
            for prop in properties:
                conn.execute(
                    """
                    INSERT INTO properties (game_id, position, owner_id, houses, is_mortgaged)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(game_id, position) DO UPDATE SET
                        owner_id = excluded.owner_id,
                        houses = excluded.houses,
                        is_mortgaged = excluded.is_mortgaged
                    """,
                    (
                        prop.game_id,
                        prop.position,
                        prop.owner_id,
                        prop.houses,
                        int(prop.is_mortgaged)
                    )
                )
            
            # Update card decks
            for deck in card_decks:
                conn.execute(
                    """
                    INSERT INTO card_decks (game_id, deck_type, card_order_json, current_index)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(game_id, deck_type) DO UPDATE SET
                        card_order_json = excluded.card_order_json,
                        current_index = excluded.current_index
                    """,
                    (
                        deck.game_id,
                        deck.deck_type,
                        deck.card_order_json,
                        deck.current_index
                    )
                )
            
            # Save state snapshot if provided
            if state_snapshot:
                conn.execute(
                    """
                    INSERT INTO game_states (game_id, state_json, turn_number)
                    VALUES (?, ?, ?)
                    """,
                    (game.id, json.dumps(state_snapshot), turn_number)
                )
    
    def load_full_game(self, game_id: str) -> dict[str, Any] | None:
        """
        Load a complete game state.
        
        Returns a dictionary with all game data, or None if not found.
        """
        game = self.get_game(game_id)
        if not game:
            return None
        
        players = self.get_players_for_game(game_id)
        properties = self.get_properties_for_game(game_id)
        card_decks = self.get_card_decks(game_id)
        latest_state = self.get_latest_game_state(game_id)
        
        return {
            "game": game,
            "players": players,
            "properties": properties,
            "card_decks": card_decks,
            "latest_snapshot": latest_state
        }
