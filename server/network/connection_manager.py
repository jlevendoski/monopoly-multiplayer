"""
Connection manager for WebSocket clients.

Tracks connected clients, their player IDs, and game associations.
Handles sending messages to individual players or broadcasting to games.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from websockets.server import WebSocketServerProtocol

from shared.protocol import Message


logger = logging.getLogger(__name__)


@dataclass
class PlayerConnection:
    """Tracks a connected player's state."""
    player_id: str
    player_name: str
    websocket: WebSocketServerProtocol
    game_id: str | None = None
    is_host: bool = False
    is_spectator: bool = False
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()


class ConnectionManager:
    """
    Manages WebSocket connections and player-to-game mappings.
    
    Provides methods for:
    - Tracking player connections
    - Associating players with games
    - Sending messages to specific players
    - Broadcasting messages to all players in a game
    - Handling disconnection and reconnection
    """
    
    def __init__(self):
        # websocket -> PlayerConnection
        self._connections: dict[WebSocketServerProtocol, PlayerConnection] = {}
        
        # player_id -> websocket (for quick lookup)
        self._player_to_socket: dict[str, WebSocketServerProtocol] = {}
        
        # game_id -> set of player_ids (includes spectators)
        self._game_players: dict[str, set[str]] = {}
        
        # Disconnected players awaiting reconnection: player_id -> PlayerConnection (without websocket)
        self._disconnected_players: dict[str, PlayerConnection] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    # =========================================================================
    # Connection Lifecycle
    # =========================================================================
    
    async def connect(
        self,
        websocket: WebSocketServerProtocol,
        player_id: str,
        player_name: str
    ) -> PlayerConnection:
        """
        Register a new player connection.
        
        If the player was previously disconnected, restores their game association.
        
        Returns:
            The PlayerConnection object
        """
        async with self._lock:
            # Check if this is a reconnection
            if player_id in self._disconnected_players:
                connection = self._disconnected_players.pop(player_id)
                connection.websocket = websocket
                connection.connected_at = datetime.utcnow()
                connection.update_activity()
                logger.info(f"Player {player_name} ({player_id}) reconnected")
            else:
                connection = PlayerConnection(
                    player_id=player_id,
                    player_name=player_name,
                    websocket=websocket,
                )
                logger.info(f"Player {player_name} ({player_id}) connected")
            
            self._connections[websocket] = connection
            self._player_to_socket[player_id] = websocket
            
            return connection
    
    async def disconnect(self, websocket: WebSocketServerProtocol) -> PlayerConnection | None:
        """
        Handle a player disconnection.
        
        The player's game association is preserved for potential reconnection.
        
        Returns:
            The PlayerConnection if found, None otherwise
        """
        async with self._lock:
            connection = self._connections.pop(websocket, None)
            
            if connection:
                self._player_to_socket.pop(connection.player_id, None)
                
                # Preserve for reconnection if they were in a game
                if connection.game_id:
                    self._disconnected_players[connection.player_id] = connection
                    logger.info(
                        f"Player {connection.player_name} ({connection.player_id}) "
                        f"disconnected from game {connection.game_id}, awaiting reconnection"
                    )
                else:
                    logger.info(
                        f"Player {connection.player_name} ({connection.player_id}) disconnected"
                    )
            
            return connection
    
    async def remove_player_completely(self, player_id: str) -> None:
        """
        Completely remove a player from tracking (e.g., when they leave a game).
        
        Unlike disconnect, this does not preserve them for reconnection.
        """
        async with self._lock:
            # Remove from active connections
            websocket = self._player_to_socket.pop(player_id, None)
            if websocket:
                connection = self._connections.pop(websocket, None)
                if connection and connection.game_id:
                    self._remove_player_from_game_internal(player_id, connection.game_id)
            
            # Remove from disconnected players
            self._disconnected_players.pop(player_id, None)
    
    # =========================================================================
    # Game Association
    # =========================================================================
    
    async def join_game(
        self,
        player_id: str,
        game_id: str,
        is_host: bool = False,
        is_spectator: bool = False
    ) -> bool:
        """
        Associate a player with a game.
        
        Returns:
            True if successful, False if player not found
        """
        async with self._lock:
            websocket = self._player_to_socket.get(player_id)
            if not websocket:
                return False
            
            connection = self._connections.get(websocket)
            if not connection:
                return False
            
            # Leave current game if in one
            if connection.game_id:
                self._remove_player_from_game_internal(player_id, connection.game_id)
            
            # Join new game
            connection.game_id = game_id
            connection.is_host = is_host
            connection.is_spectator = is_spectator
            
            if game_id not in self._game_players:
                self._game_players[game_id] = set()
            self._game_players[game_id].add(player_id)
            
            logger.info(
                f"Player {connection.player_name} ({player_id}) joined game {game_id}"
                f"{' as host' if is_host else ''}{' as spectator' if is_spectator else ''}"
            )
            
            return True
    
    async def leave_game(self, player_id: str) -> str | None:
        """
        Remove a player from their current game.
        
        Returns:
            The game_id they left, or None if not in a game
        """
        async with self._lock:
            websocket = self._player_to_socket.get(player_id)
            if not websocket:
                # Check disconnected players
                connection = self._disconnected_players.get(player_id)
                if connection and connection.game_id:
                    game_id = connection.game_id
                    self._remove_player_from_game_internal(player_id, game_id)
                    connection.game_id = None
                    # Remove from disconnected since they left the game
                    self._disconnected_players.pop(player_id, None)
                    return game_id
                return None
            
            connection = self._connections.get(websocket)
            if not connection or not connection.game_id:
                return None
            
            game_id = connection.game_id
            self._remove_player_from_game_internal(player_id, game_id)
            connection.game_id = None
            connection.is_host = False
            connection.is_spectator = False
            
            logger.info(f"Player {connection.player_name} ({player_id}) left game {game_id}")
            
            return game_id
    
    def _remove_player_from_game_internal(self, player_id: str, game_id: str) -> None:
        """Internal helper to remove player from game tracking (no lock)."""
        if game_id in self._game_players:
            self._game_players[game_id].discard(player_id)
            if not self._game_players[game_id]:
                del self._game_players[game_id]
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    def get_connection(self, websocket: WebSocketServerProtocol) -> PlayerConnection | None:
        """Get connection info for a websocket."""
        return self._connections.get(websocket)
    
    def get_connection_by_player_id(self, player_id: str) -> PlayerConnection | None:
        """Get connection info for a player ID."""
        websocket = self._player_to_socket.get(player_id)
        if websocket:
            return self._connections.get(websocket)
        return None
    
    def get_player_id(self, websocket: WebSocketServerProtocol) -> str | None:
        """Get player ID for a websocket."""
        connection = self._connections.get(websocket)
        return connection.player_id if connection else None
    
    def get_game_id(self, player_id: str) -> str | None:
        """Get game ID for a player."""
        connection = self.get_connection_by_player_id(player_id)
        if connection:
            return connection.game_id
        # Check disconnected players
        disconnected = self._disconnected_players.get(player_id)
        return disconnected.game_id if disconnected else None
    
    def get_players_in_game(self, game_id: str) -> set[str]:
        """Get all player IDs in a game (including disconnected and spectators)."""
        return self._game_players.get(game_id, set()).copy()
    
    def get_connected_players_in_game(self, game_id: str) -> list[PlayerConnection]:
        """Get all currently connected players in a game."""
        player_ids = self._game_players.get(game_id, set())
        connections = []
        for player_id in player_ids:
            conn = self.get_connection_by_player_id(player_id)
            if conn:
                connections.append(conn)
        return connections
    
    def get_host(self, game_id: str) -> PlayerConnection | None:
        """Get the host of a game."""
        for conn in self.get_connected_players_in_game(game_id):
            if conn.is_host:
                return conn
        return None
    
    def is_player_connected(self, player_id: str) -> bool:
        """Check if a player is currently connected."""
        return player_id in self._player_to_socket
    
    def is_player_in_game(self, player_id: str, game_id: str) -> bool:
        """Check if a player is in a specific game."""
        return player_id in self._game_players.get(game_id, set())
    
    def get_disconnected_players_in_game(self, game_id: str) -> list[PlayerConnection]:
        """Get all disconnected players for a game."""
        return [
            conn for conn in self._disconnected_players.values()
            if conn.game_id == game_id
        ]
    
    # =========================================================================
    # Messaging
    # =========================================================================
    
    async def send_to_player(self, player_id: str, message: Message | dict | str) -> bool:
        """
        Send a message to a specific player.
        
        Args:
            player_id: The player to send to
            message: Message object, dict, or JSON string
            
        Returns:
            True if sent successfully, False if player not connected
        """
        websocket = self._player_to_socket.get(player_id)
        if not websocket:
            return False
        
        return await self._send_to_websocket(websocket, message)
    
    async def send_to_connection(
        self,
        websocket: WebSocketServerProtocol,
        message: Message | dict | str
    ) -> bool:
        """
        Send a message to a specific websocket connection.
        
        Returns:
            True if sent successfully, False on error
        """
        return await self._send_to_websocket(websocket, message)
    
    async def broadcast_to_game(
        self,
        game_id: str,
        message: Message | dict | str,
        exclude_player_id: str | None = None,
        exclude_spectators: bool = False
    ) -> int:
        """
        Broadcast a message to all connected players in a game.
        
        Args:
            game_id: The game to broadcast to
            message: Message object, dict, or JSON string
            exclude_player_id: Optional player to exclude from broadcast
            exclude_spectators: If True, don't send to spectators
            
        Returns:
            Number of players the message was sent to
        """
        connections = self.get_connected_players_in_game(game_id)
        sent_count = 0
        
        for conn in connections:
            if exclude_player_id and conn.player_id == exclude_player_id:
                continue
            if exclude_spectators and conn.is_spectator:
                continue
            
            if await self._send_to_websocket(conn.websocket, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_all(self, message: Message | dict | str) -> int:
        """
        Broadcast a message to all connected players.
        
        Returns:
            Number of players the message was sent to
        """
        sent_count = 0
        for websocket in list(self._connections.keys()):
            if await self._send_to_websocket(websocket, message):
                sent_count += 1
        return sent_count
    
    async def _send_to_websocket(
        self,
        websocket: WebSocketServerProtocol,
        message: Message | dict | str
    ) -> bool:
        """Internal helper to send a message to a websocket."""
        try:
            if isinstance(message, Message):
                data = message.to_json()
            elif isinstance(message, dict):
                import json
                data = json.dumps(message)
            else:
                data = message
            
            await websocket.send(data)
            
            # Update activity timestamp
            connection = self._connections.get(websocket)
            if connection:
                connection.update_activity()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    # =========================================================================
    # Host Management
    # =========================================================================
    
    async def transfer_host(self, game_id: str, new_host_id: str) -> bool:
        """
        Transfer host privileges to another player.
        
        Returns:
            True if successful, False if player not found or not in game
        """
        async with self._lock:
            if not self.is_player_in_game(new_host_id, game_id):
                return False
            
            # Remove host from current host
            for conn in self.get_connected_players_in_game(game_id):
                if conn.is_host:
                    conn.is_host = False
                    break
            
            # Set new host
            new_host_conn = self.get_connection_by_player_id(new_host_id)
            if new_host_conn:
                new_host_conn.is_host = True
                logger.info(f"Host transferred to {new_host_conn.player_name} in game {game_id}")
                return True
            
            return False
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._connections),
            "total_players": len(self._player_to_socket),
            "active_games": len(self._game_players),
            "disconnected_awaiting_reconnect": len(self._disconnected_players),
            "players_per_game": {
                game_id: len(players) 
                for game_id, players in self._game_players.items()
            },
        }
