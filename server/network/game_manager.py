"""
Game manager for handling multiple game instances.

Manages game lifecycle: creation, joining, starting, saving, and loading.
Integrates with the persistence layer for auto-save and game recovery.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from server.game_engine import Game, Player
from server.persistence import (
    GameRepository,
    GameRecord,
    PlayerRecord,
    PropertyRecord,
    CardDeckRecord,
    GameSummary,
    get_database,
)
from shared.protocol import GameSettings
from shared.enums import GamePhase, PlayerState


logger = logging.getLogger(__name__)


@dataclass
class ManagedGame:
    """Wrapper around a Game with additional management metadata."""
    game: Game
    host_player_id: str
    settings: GameSettings
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_saved_at: datetime | None = None
    last_saved_turn: int = 0
    
    @property
    def game_id(self) -> str:
        return self.game.id
    
    @property
    def is_started(self) -> bool:
        return self.game.phase != GamePhase.WAITING
    
    @property
    def is_finished(self) -> bool:
        return self.game.phase == GamePhase.GAME_OVER
    
    @property
    def player_count(self) -> int:
        return len(self.game.players)
    
    @property
    def needs_save(self) -> bool:
        """Check if game has unsaved changes."""
        return self.game.turn_number > self.last_saved_turn


class GameManager:
    """
    Manages multiple game instances and their persistence.
    
    Provides methods for:
    - Creating and configuring new games
    - Joining players to games
    - Starting games
    - Saving and loading game state
    - Listing available games
    """
    
    def __init__(self, repository: GameRepository | None = None):
        # game_id -> ManagedGame
        self._games: dict[str, ManagedGame] = {}
        
        # player_id -> game_id (for quick lookup)
        self._player_games: dict[str, str] = {}
        
        # Persistence
        self._repository = repository or GameRepository(get_database())
    
    # =========================================================================
    # Game Creation
    # =========================================================================
    
    def create_game(
        self,
        name: str,
        host_player_id: str,
        host_player_name: str,
        settings: GameSettings | None = None
    ) -> tuple[bool, str, ManagedGame | None]:
        """
        Create a new game and add the host as the first player.
        
        Args:
            name: Display name for the game
            host_player_id: Player ID of the host
            host_player_name: Display name of the host
            settings: Optional game settings
            
        Returns:
            Tuple of (success, message, ManagedGame or None)
        """
        # Check if host is already in a game
        if host_player_id in self._player_games:
            return False, "You are already in a game", None
        
        settings = settings or GameSettings()
        
        # Create the game
        game = Game(name=name, max_players=settings.max_players)
        
        # Add host as first player
        success, msg, player = game.add_player(host_player_name, player_id=host_player_id)
        if not success:
            return False, msg, None
        
        # Create managed wrapper
        managed = ManagedGame(
            game=game,
            host_player_id=host_player_id,
            settings=settings,
        )
        
        self._games[game.id] = managed
        self._player_games[host_player_id] = game.id
        
        logger.info(f"Game '{name}' ({game.id}) created by {host_player_name}")
        
        return True, f"Game '{name}' created", managed
    
    # =========================================================================
    # Joining and Leaving
    # =========================================================================
    
    def join_game(
        self,
        game_id: str,
        player_id: str,
        player_name: str,
        as_spectator: bool = False
    ) -> tuple[bool, str, Player | None]:
        """
        Add a player to an existing game.
        
        Args:
            game_id: ID of the game to join
            player_id: Player's unique ID
            player_name: Player's display name
            as_spectator: If True, join as spectator (if allowed)
            
        Returns:
            Tuple of (success, message, Player or None)
        """
        managed = self._games.get(game_id)
        if not managed:
            return False, "Game not found", None
        
        # Check if player is already in a game
        if player_id in self._player_games:
            if self._player_games[player_id] == game_id:
                # Already in this game - might be reconnecting
                player = managed.game.players.get(player_id)
                if player:
                    return True, "Reconnected to game", player
            return False, "You are already in another game", None
        
        if as_spectator:
            if not managed.settings.allow_spectators:
                return False, "This game does not allow spectators", None
            # Spectators don't get added as players - just tracked by ConnectionManager
            self._player_games[player_id] = game_id
            return True, "Joined as spectator", None
        
        # Check if game has started
        if managed.is_started:
            return False, "Game has already started", None
        
        # Add player to game
        success, msg, player = managed.game.add_player(player_name, player_id=player_id)
        if not success:
            return False, msg, None
        
        self._player_games[player_id] = game_id
        
        logger.info(f"Player {player_name} ({player_id}) joined game {game_id}")
        
        return True, msg, player
    
    def leave_game(self, player_id: str) -> tuple[bool, str, str | None]:
        """
        Remove a player from their current game.
        
        Args:
            player_id: Player's unique ID
            
        Returns:
            Tuple of (success, message, game_id or None)
        """
        game_id = self._player_games.get(player_id)
        if not game_id:
            return False, "You are not in a game", None
        
        managed = self._games.get(game_id)
        if not managed:
            # Clean up stale reference
            del self._player_games[player_id]
            return False, "Game not found", None
        
        # Remove from game
        success, msg = managed.game.remove_player(player_id)
        del self._player_games[player_id]
        
        # Log if host left but don't reassign - they can reconnect indefinitely
        if player_id == managed.host_player_id:
            logger.info(f"Host {player_id} left game {game_id}, awaiting reconnection")
        
        # Only clean up empty games that haven't started
        if not managed.is_started and managed.player_count == 0:
            del self._games[game_id]
            logger.info(f"Empty game {game_id} removed")
        
        logger.info(f"Player {player_id} left game {game_id}")
        
        return True, msg, game_id
    
    def remove_player(self, game_id: str, player_id: str, remover_id: str) -> tuple[bool, str]:
        """
        Remove a player from a game (host privilege).
        
        Args:
            game_id: Game ID
            player_id: Player to remove
            remover_id: Player requesting the removal (must be host)
            
        Returns:
            Tuple of (success, message)
        """
        managed = self._games.get(game_id)
        if not managed:
            return False, "Game not found"
        
        if remover_id != managed.host_player_id:
            return False, "Only the host can remove players"
        
        if player_id == managed.host_player_id:
            return False, "Host cannot remove themselves"
        
        if player_id not in self._player_games:
            return False, "Player not in game"
        
        success, msg = managed.game.remove_player(player_id)
        if success:
            del self._player_games[player_id]
        
        return success, msg
    
    # =========================================================================
    # Game Flow
    # =========================================================================
    
    def start_game(self, game_id: str, requester_id: str) -> tuple[bool, str]:
        """
        Start a game (host only).
        
        Args:
            game_id: Game to start
            requester_id: Player requesting the start (must be host)
            
        Returns:
            Tuple of (success, message)
        """
        managed = self._games.get(game_id)
        if not managed:
            return False, "Game not found"
        
        if requester_id != managed.host_player_id:
            return False, "Only the host can start the game"
        
        success, msg = managed.game.start_game()
        
        if success:
            logger.info(f"Game {game_id} started")
            # Auto-save initial state
            self.save_game(game_id)
        
        return success, msg
    
    def get_game(self, game_id: str) -> ManagedGame | None:
        """Get a managed game by ID."""
        return self._games.get(game_id)
    
    def get_game_for_player(self, player_id: str) -> ManagedGame | None:
        """Get the game a player is in."""
        game_id = self._player_games.get(player_id)
        if game_id:
            return self._games.get(game_id)
        return None
    
    def is_host(self, game_id: str, player_id: str) -> bool:
        """Check if a player is the host of a game."""
        managed = self._games.get(game_id)
        return managed is not None and managed.host_player_id == player_id
    
    # =========================================================================
    # Persistence
    # =========================================================================
    
    def save_game(self, game_id: str) -> tuple[bool, str]:
        """
        Save a game to the database.
        
        Args:
            game_id: Game to save
            
        Returns:
            Tuple of (success, message)
        """
        managed = self._games.get(game_id)
        if not managed:
            return False, "Game not found"
        
        try:
            game = managed.game
            
            # Create game record
            game_record = GameRecord(
                id=game.id,
                name=game.name,
                status=game.phase.value,
                current_player_index=game.current_player_index,
                winner_id=game.winner_id,
                settings_json=json.dumps(managed.settings.to_dict()),
            )
            
            # Create player records
            player_records = []
            for idx, player_id in enumerate(game.player_order):
                player = game.players.get(player_id)
                if player:
                    player_records.append(PlayerRecord(
                        id=player.id,
                        game_id=game.id,
                        name=player.name,
                        token="default",  # TODO: Add token selection
                        turn_order=idx,
                        position=player.position,
                        money=player.money,
                        is_bankrupt=player.state == PlayerState.BANKRUPT,
                        is_in_jail=player.state == PlayerState.IN_JAIL,
                        jail_turns=player.jail_turns,
                        get_out_of_jail_cards=player.jail_cards,
                        connected=True,  # Will be updated by ConnectionManager
                    ))
            
            # Create property records
            property_records = []
            for pos, prop in game.board.properties.items():
                if prop.owner_id:  # Only save owned properties
                    property_records.append(PropertyRecord(
                        game_id=game.id,
                        position=pos,
                        owner_id=prop.owner_id,
                        houses=5 if prop.has_hotel else prop.houses,
                        is_mortgaged=prop.is_mortgaged,
                    ))
            
            # Create card deck records
            # The CardManager uses draw/discard piles, so we save the counts
            # The full state is captured in the snapshot anyway
            card_decks = [
                CardDeckRecord(
                    game_id=game.id,
                    deck_type="chance",
                    card_order_json=json.dumps({
                        "cards_remaining": len(game.cards.chance.cards),
                        "discard_count": len(game.cards.chance.discard),
                    }),
                    current_index=len(game.cards.chance.discard),
                ),
                CardDeckRecord(
                    game_id=game.id,
                    deck_type="community_chest",
                    card_order_json=json.dumps({
                        "cards_remaining": len(game.cards.community_chest.cards),
                        "discard_count": len(game.cards.community_chest.discard),
                    }),
                    current_index=len(game.cards.community_chest.discard),
                ),
            ]
            
            # Full game state snapshot
            state_snapshot = game.to_dict()
            
            # Save everything
            self._repository.save_full_game(
                game=game_record,
                players=player_records,
                properties=property_records,
                card_decks=card_decks,
                state_snapshot=state_snapshot,
                turn_number=game.turn_number,
            )
            
            managed.last_saved_at = datetime.utcnow()
            managed.last_saved_turn = game.turn_number
            
            logger.info(f"Game {game_id} saved at turn {game.turn_number}")
            
            return True, "Game saved"
            
        except Exception as e:
            logger.error(f"Failed to save game {game_id}: {e}")
            return False, f"Failed to save game: {e}"
    
    def auto_save_if_needed(self, game_id: str) -> bool:
        """
        Auto-save game if there are unsaved changes.
        
        Called after each turn. Returns True if saved.
        """
        managed = self._games.get(game_id)
        if managed and managed.needs_save:
            success, _ = self.save_game(game_id)
            return success
        return False
    
    def load_game(self, game_id: str) -> tuple[bool, str, ManagedGame | None]:
        """
        Load a game from the database.
        
        Args:
            game_id: Game to load
            
        Returns:
            Tuple of (success, message, ManagedGame or None)
        """
        # Check if already loaded
        if game_id in self._games:
            return True, "Game already loaded", self._games[game_id]
        
        try:
            # Get latest snapshot
            snapshot = self._repository.get_latest_game_state(game_id)
            if not snapshot:
                return False, "Game not found or no saved state", None
            
            # Load game from snapshot
            state = json.loads(snapshot.state_json)
            game = Game.from_dict(state)
            
            # Get game record for settings and host info
            game_record = self._repository.get_game(game_id)
            if not game_record:
                return False, "Game record not found", None
            
            settings = GameSettings.from_dict(json.loads(game_record.settings_json))
            
            # Determine host (first player in order, or from saved data)
            host_id = game.player_order[0] if game.player_order else None
            if not host_id:
                return False, "No players in saved game", None
            
            managed = ManagedGame(
                game=game,
                host_player_id=host_id,
                settings=settings,
                last_saved_at=snapshot.created_at,
                last_saved_turn=snapshot.turn_number,
            )
            
            self._games[game_id] = managed
            
            # Re-establish player-game mappings
            for player_id in game.players:
                self._player_games[player_id] = game_id
            
            logger.info(f"Game {game_id} loaded from turn {snapshot.turn_number}")
            
            return True, "Game loaded", managed
            
        except Exception as e:
            logger.error(f"Failed to load game {game_id}: {e}")
            return False, f"Failed to load game: {e}", None
    
    def delete_game(self, game_id: str, requester_id: str) -> tuple[bool, str]:
        """
        Delete a game (host only, or if game is finished).
        
        Args:
            game_id: Game to delete
            requester_id: Player requesting deletion
            
        Returns:
            Tuple of (success, message)
        """
        managed = self._games.get(game_id)
        
        if managed:
            if requester_id != managed.host_player_id and not managed.is_finished:
                return False, "Only the host can delete an active game"
            
            # Remove player mappings
            for player_id in list(self._player_games.keys()):
                if self._player_games[player_id] == game_id:
                    del self._player_games[player_id]
            
            del self._games[game_id]
        
        # Delete from database
        self._repository.delete_game(game_id)
        
        logger.info(f"Game {game_id} deleted")
        
        return True, "Game deleted"
    
    # =========================================================================
    # Listing
    # =========================================================================
    
    def list_games(
        self,
        status: str | None = None,
        include_db: bool = True
    ) -> list[dict[str, Any]]:
        """
        List available games.
        
        Args:
            status: Filter by status (e.g., "WAITING", "PRE_ROLL")
            include_db: If True, also include saved games from database
            
        Returns:
            List of game summaries
        """
        games = []
        
        # In-memory games
        for managed in self._games.values():
            if status and managed.game.phase.value != status:
                continue
            
            games.append({
                "id": managed.game_id,
                "name": managed.game.name,
                "status": managed.game.phase.value,
                "player_count": managed.player_count,
                "max_players": managed.settings.max_players,
                "host_id": managed.host_player_id,
                "is_started": managed.is_started,
                "is_finished": managed.is_finished,
                "allow_spectators": managed.settings.allow_spectators,
                "in_memory": True,
            })
        
        # Database games (not already loaded)
        if include_db:
            loaded_ids = set(self._games.keys())
            db_games = self._repository.list_games(status=status)
            
            for summary in db_games:
                if summary.id not in loaded_ids:
                    games.append({
                        "id": summary.id,
                        "name": summary.name,
                        "status": summary.status,
                        "player_count": summary.player_count,
                        "max_players": 4,  # Default, actual value in settings
                        "host_id": None,  # Unknown until loaded
                        "is_started": summary.status != "WAITING",
                        "is_finished": summary.status == "GAME_OVER",
                        "allow_spectators": False,  # Unknown until loaded
                        "in_memory": False,
                    })
        
        return games
    
    def list_joinable_games(self) -> list[dict[str, Any]]:
        """List games that can be joined (waiting, not full)."""
        games = []
        
        for managed in self._games.values():
            if managed.is_started:
                continue
            if managed.player_count >= managed.settings.max_players:
                continue
            
            games.append({
                "id": managed.game_id,
                "name": managed.game.name,
                "player_count": managed.player_count,
                "max_players": managed.settings.max_players,
                "host_id": managed.host_player_id,
                "allow_spectators": managed.settings.allow_spectators,
            })
        
        return games
    
    # =========================================================================
    # Bank Assignment (Host Privilege)
    # =========================================================================
    
    def assign_banker(
        self,
        game_id: str,
        banker_id: str,
        requester_id: str
    ) -> tuple[bool, str]:
        """
        Assign a player as the banker (host privilege).
        
        Note: This is mainly for display/role purposes. The game engine
        handles all banking automatically.
        
        Args:
            game_id: Game ID
            banker_id: Player to assign as banker
            requester_id: Player requesting (must be host)
            
        Returns:
            Tuple of (success, message)
        """
        managed = self._games.get(game_id)
        if not managed:
            return False, "Game not found"
        
        if requester_id != managed.host_player_id:
            return False, "Only the host can assign the banker"
        
        if banker_id not in managed.game.players:
            return False, "Player not in game"
        
        # For now, just log it. Could add a banker_id field to ManagedGame
        # if we want to track and display this.
        logger.info(f"Player {banker_id} assigned as banker in game {game_id}")
        
        return True, f"Banker assigned"
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> dict[str, Any]:
        """Get game manager statistics."""
        active = sum(1 for g in self._games.values() if g.is_started and not g.is_finished)
        waiting = sum(1 for g in self._games.values() if not g.is_started)
        finished = sum(1 for g in self._games.values() if g.is_finished)
        
        return {
            "total_games_in_memory": len(self._games),
            "active_games": active,
            "waiting_games": waiting,
            "finished_games": finished,
            "total_players_in_games": len(self._player_games),
        }
