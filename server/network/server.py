"""
WebSocket server for Monopoly multiplayer.

Main entry point that ties together connection management,
game management, and message handling.
"""

import asyncio
import json
import logging
import signal
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol, serve

from server.network.connection_manager import ConnectionManager
from server.network.game_manager import GameManager
from server.network.message_handler import MessageHandler
from server.persistence import init_database, GameRepository
from server.config import settings
from shared.protocol import (
    Message,
    ErrorMessage,
    GameStateMessage,
    PlayerDisconnectedMessage,
    PlayerReconnectedMessage,
)
from shared.enums import MessageType


logger = logging.getLogger(__name__)


class MonopolyServer:
    """
    WebSocket server for Monopoly multiplayer games.
    
    Handles client connections, routes messages, and manages
    the game lifecycle.
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db_path: str = None
    ):
        self.host = host or settings.HOST
        self.port = port or settings.PORT
        
        # Initialize database
        db = init_database(db_path)
        self._repository = GameRepository(db)
        
        # Initialize managers
        self._connections = ConnectionManager()
        self._games = GameManager(self._repository)
        self._handler = MessageHandler(self._games, self._connections)
        
        # Server state
        self._server = None
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        self._shutdown_event.clear()
        
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        )
        
        logger.info(f"Monopoly server started on ws://{self.host}:{self.port}")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
    
    async def stop(self) -> None:
        """Stop the server gracefully."""
        logger.info("Shutting down server...")
        self._running = False
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        self._shutdown_event.set()
        logger.info("Server stopped")
    
    def request_shutdown(self) -> None:
        """Request server shutdown (can be called from signal handler)."""
        asyncio.create_task(self.stop())
    
    async def _handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handle a client connection.
        
        The first message must be a CONNECT message with player_id and player_name.
        After that, messages are routed through the message handler.
        """
        player_id = None
        
        try:
            # Wait for initial connect message
            player_id = await self._handle_connect(websocket)
            
            if not player_id:
                return
            
            # Handle messages until disconnect
            async for raw_message in websocket:
                if not self._running:
                    break
                
                await self._handle_message(websocket, player_id, raw_message)
                
        except websockets.ConnectionClosed:
            logger.debug(f"Connection closed for player {player_id}")
        except Exception as e:
            logger.exception(f"Error handling client {player_id}: {e}")
        finally:
            if player_id:
                await self._handle_disconnect(websocket, player_id)
    
    async def _handle_connect(self, websocket: WebSocketServerProtocol) -> str | None:
        """
        Handle initial connection and authentication.
        
        Expects a CONNECT message with player_id and player_name.
        Returns player_id if successful, None otherwise.
        """
        try:
            # Wait for connect message with timeout
            raw = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            data = json.loads(raw)
            
            if data.get("type") != MessageType.CONNECT.value:
                await self._send_error(
                    websocket,
                    "First message must be CONNECT",
                    "CONNECT_REQUIRED"
                )
                return None
            
            player_id = data.get("data", {}).get("player_id")
            player_name = data.get("data", {}).get("player_name", "Player")
            
            if not player_id:
                await self._send_error(
                    websocket,
                    "player_id is required",
                    "MISSING_PLAYER_ID"
                )
                return None
            
            # Register connection
            connection = await self._connections.connect(websocket, player_id, player_name)
            
            # Check if reconnecting to a game
            game_id = connection.game_id
            if game_id:
                managed = self._games.get_game(game_id)
                if managed:
                    # Notify other players of reconnection
                    await self._connections.broadcast_to_game(
                        game_id,
                        PlayerReconnectedMessage.create(player_id, player_name),
                        exclude_player_id=player_id
                    )
                    
                    # Send current game state to reconnected player
                    state_msg = GameStateMessage.create(
                        managed.game.get_state_for_player(player_id)
                    )
                    await websocket.send(state_msg.to_json())
                    
                    logger.info(f"Player {player_name} ({player_id}) reconnected to game {game_id}")
            
            # Send connect acknowledgment
            await websocket.send(json.dumps({
                "type": MessageType.CONNECT.value,
                "data": {
                    "success": True,
                    "player_id": player_id,
                    "player_name": player_name,
                    "reconnected_to_game": game_id,
                }
            }))
            
            logger.info(f"Player {player_name} ({player_id}) connected")
            
            return player_id
            
        except asyncio.TimeoutError:
            await self._send_error(websocket, "Connection timeout", "TIMEOUT")
            return None
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON", "PARSE_ERROR")
            return None
        except Exception as e:
            logger.exception(f"Error during connect: {e}")
            await self._send_error(websocket, str(e), "CONNECT_ERROR")
            return None
    
    async def _handle_message(
        self,
        websocket: WebSocketServerProtocol,
        player_id: str,
        raw_message: str
    ) -> None:
        """Handle an incoming message from a connected player."""
        try:
            # Process message through handler
            result = await self._handler.handle_message(player_id, raw_message)
            
            # Send response to requester
            if result.response:
                await websocket.send(result.response.to_json())
            
            # Get game for broadcasts
            game_id = self._connections.get_game_id(player_id)
            
            if game_id:
                # Send specific broadcasts
                if result.broadcasts:
                    for broadcast in result.broadcasts:
                        await self._connections.broadcast_to_game(
                            game_id,
                            broadcast,
                            exclude_player_id=player_id  # Requester already got response
                        )
                
                # Broadcast full state if requested
                if result.broadcast_state:
                    managed = self._games.get_game(game_id)
                    if managed:
                        await self._broadcast_state_to_game(game_id, managed)
                
                # Auto-save if needed
                if result.should_save:
                    self._games.auto_save_if_needed(game_id)
                    
        except Exception as e:
            logger.exception(f"Error handling message from {player_id}: {e}")
            await self._send_error(websocket, f"Internal error: {e}", "INTERNAL_ERROR")
    
    async def _handle_disconnect(
        self,
        websocket: WebSocketServerProtocol,
        player_id: str
    ) -> None:
        """Handle player disconnection."""
        connection = await self._connections.disconnect(websocket)
        
        if connection and connection.game_id:
            # Notify other players
            await self._connections.broadcast_to_game(
                connection.game_id,
                PlayerDisconnectedMessage.create(player_id, connection.player_name),
            )
            
            # Save game state
            self._games.auto_save_if_needed(connection.game_id)
            
            logger.info(
                f"Player {connection.player_name} ({player_id}) disconnected "
                f"from game {connection.game_id}"
            )
    
    async def _broadcast_state_to_game(self, game_id: str, managed) -> None:
        """Broadcast game state to all players in a game."""
        connections = self._connections.get_connected_players_in_game(game_id)
        
        for conn in connections:
            try:
                state_msg = GameStateMessage.create(
                    managed.game.get_state_for_player(conn.player_id)
                )
                await conn.websocket.send(state_msg.to_json())
            except Exception as e:
                logger.error(f"Failed to send state to {conn.player_id}: {e}")
    
    async def _send_error(
        self,
        websocket: WebSocketServerProtocol,
        message: str,
        code: str
    ) -> None:
        """Send an error message to a websocket."""
        try:
            error = ErrorMessage.create(message, code)
            await websocket.send(error.to_json())
        except Exception:
            pass  # Connection might already be closed
    
    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "running": self._running,
            "connections": self._connections.get_stats(),
            "games": self._games.get_stats(),
        }


async def run_server(host: str = None, port: int = None, db_path: str = None) -> None:
    """
    Run the Monopoly server.
    
    Sets up signal handlers for graceful shutdown.
    """
    server = MonopolyServer(host, port, db_path)
    
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, server.request_shutdown)
    
    try:
        await server.start()
    finally:
        # Clean up signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


def main():
    """Entry point for running the server."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print(f"Starting Monopoly server on ws://{settings.HOST}:{settings.PORT}")
    print("Press Ctrl+C to stop")
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped")


if __name__ == "__main__":
    main()
