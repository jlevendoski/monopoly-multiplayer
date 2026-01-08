"""
WebSocket client for connecting to the Monopoly server.

Handles connection, reconnection, and message passing.
Uses Qt signals to communicate with the GUI thread.
"""

import asyncio
import json
import logging
import uuid
from enum import Enum, auto
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal

import websockets
from websockets.client import WebSocketClientProtocol

from client.config import settings
from shared.protocol import Message, parse_message
from shared.enums import MessageType


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    FAILED = auto()


class NetworkClient(QObject):
    """
    WebSocket client for Monopoly server communication.
    
    Emits Qt signals for GUI updates:
    - connection_changed: Connection state changed
    - message_received: Server message received
    - error_occurred: Error happened
    """
    
    # Qt Signals
    connection_changed = pyqtSignal(ConnectionState)
    message_received = pyqtSignal(dict)  # Parsed message data
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._player_id: Optional[str] = None
        self._player_name: Optional[str] = None
        self._current_game_id: Optional[str] = None
        
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        
        # Pending requests waiting for responses
        self._pending_requests: dict[str, asyncio.Future] = {}
    
    @property
    def state(self) -> ConnectionState:
        return self._state
    
    @property
    def player_id(self) -> Optional[str]:
        return self._player_id
    
    @property
    def player_name(self) -> Optional[str]:
        return self._player_name
    
    @property
    def current_game_id(self) -> Optional[str]:
        return self._current_game_id
    
    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED
    
    def _set_state(self, state: ConnectionState) -> None:
        """Update connection state and emit signal."""
        if self._state != state:
            self._state = state
            self.connection_changed.emit(state)
    
    async def connect(self, player_name: str, player_id: Optional[str] = None) -> bool:
        """
        Connect to the server.
        
        Args:
            player_name: Display name for this player
            player_id: Optional player ID for reconnection
            
        Returns:
            True if connection successful
        """
        if self._state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            return self._state == ConnectionState.CONNECTED
        
        self._player_name = player_name
        self._player_id = player_id or str(uuid.uuid4())
        self._should_reconnect = True
        
        return await self._do_connect()
    
    async def _do_connect(self) -> bool:
        """Perform the actual connection."""
        self._set_state(ConnectionState.CONNECTING)
        
        try:
            self._websocket = await websockets.connect(
                settings.server_url,
                ping_interval=30,
                ping_timeout=10,
            )
            
            # Send CONNECT message
            connect_msg = {
                "type": MessageType.CONNECT.value,
                "data": {
                    "player_id": self._player_id,
                    "player_name": self._player_name,
                }
            }
            await self._websocket.send(json.dumps(connect_msg))
            
            # Wait for response
            response = await asyncio.wait_for(self._websocket.recv(), timeout=10.0)
            data = json.loads(response)
            
            if data.get("type") == MessageType.CONNECT.value:
                if data.get("data", {}).get("success"):
                    self._set_state(ConnectionState.CONNECTED)
                    
                    # Check if reconnected to a game
                    reconnected_game = data.get("data", {}).get("reconnected_to_game")
                    if reconnected_game:
                        self._current_game_id = reconnected_game
                        logger.info(f"Reconnected to game {reconnected_game}")
                    
                    # Start receive loop
                    self._receive_task = asyncio.create_task(self._receive_loop())
                    
                    logger.info(f"Connected as {self._player_name} ({self._player_id})")
                    return True
                else:
                    error = data.get("data", {}).get("message", "Connection rejected")
                    self.error_occurred.emit(error)
            elif data.get("type") == MessageType.ERROR.value:
                error = data.get("data", {}).get("message", "Connection error")
                self.error_occurred.emit(error)
            
            self._set_state(ConnectionState.FAILED)
            return False
            
        except asyncio.TimeoutError:
            self.error_occurred.emit("Connection timeout")
            self._set_state(ConnectionState.FAILED)
            return False
        except Exception as e:
            logger.exception(f"Connection failed: {e}")
            self.error_occurred.emit(f"Connection failed: {e}")
            self._set_state(ConnectionState.FAILED)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._should_reconnect = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        self._current_game_id = None
        self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Disconnected from server")
    
    async def _receive_loop(self) -> None:
        """Receive messages from server."""
        try:
            async for raw_message in self._websocket:
                try:
                    data = json.loads(raw_message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.exception(f"Error handling message: {e}")
                    
        except websockets.ConnectionClosed:
            logger.info("Connection closed by server")
        except Exception as e:
            logger.exception(f"Receive loop error: {e}")
        finally:
            if self._should_reconnect:
                self._reconnect_task = asyncio.create_task(self._reconnect())
            else:
                self._set_state(ConnectionState.DISCONNECTED)
    
    async def _handle_message(self, data: dict) -> None:
        """Handle an incoming message."""
        msg_type = data.get("type")
        request_id = data.get("request_id")
        
        # Check if this is a response to a pending request
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.done():
                future.set_result(data)
            return
        
        # Update local state based on message type
        if msg_type == MessageType.GAME_STATE.value:
            game_id = data.get("data", {}).get("game_id")
            if game_id:
                self._current_game_id = game_id
        
        elif msg_type == MessageType.LEAVE_GAME.value:
            # We left or were kicked
            if data.get("data", {}).get("player_id") == self._player_id:
                self._current_game_id = None
        
        elif msg_type == MessageType.ERROR.value:
            error_msg = data.get("data", {}).get("message", "Unknown error")
            self.error_occurred.emit(error_msg)
        
        # Emit signal for GUI to handle
        self.message_received.emit(data)
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect to the server."""
        self._set_state(ConnectionState.RECONNECTING)
        
        for attempt in range(settings.reconnect_attempts):
            logger.info(f"Reconnection attempt {attempt + 1}/{settings.reconnect_attempts}")
            
            await asyncio.sleep(settings.reconnect_delay)
            
            if not self._should_reconnect:
                break
            
            if await self._do_connect():
                return
        
        self._set_state(ConnectionState.FAILED)
        self.error_occurred.emit("Failed to reconnect to server")
    
    async def send(self, message: Message | dict) -> None:
        """
        Send a message to the server.
        
        Args:
            message: Message object or dict to send
        """
        if not self._websocket or self._state != ConnectionState.CONNECTED:
            self.error_occurred.emit("Not connected to server")
            return
        
        try:
            if isinstance(message, Message):
                data = message.to_json()
            else:
                data = json.dumps(message)
            
            await self._websocket.send(data)
            
        except Exception as e:
            logger.exception(f"Failed to send message: {e}")
            self.error_occurred.emit(f"Failed to send: {e}")
    
    async def send_and_wait(
        self, 
        message: Message | dict, 
        timeout: float = 10.0
    ) -> Optional[dict]:
        """
        Send a message and wait for the response.
        
        Args:
            message: Message to send
            timeout: Seconds to wait for response
            
        Returns:
            Response data or None on timeout/error
        """
        # Generate request ID if not present
        if isinstance(message, Message):
            if not message.request_id:
                message.request_id = str(uuid.uuid4())
            request_id = message.request_id
            data = message.to_dict()
        else:
            if "request_id" not in message:
                message["request_id"] = str(uuid.uuid4())
            request_id = message["request_id"]
            data = message
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            await self.send(data)
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            self.error_occurred.emit("Request timed out")
            return None
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            logger.exception(f"Request failed: {e}")
            return None
    
    # =========================================================================
    # Convenience methods for common actions
    # =========================================================================
    
    async def list_games(self) -> Optional[list]:
        """Get list of available games."""
        response = await self.send_and_wait({
            "type": MessageType.LIST_GAMES.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_LIST.value:
            return response.get("data", {}).get("games", [])
        return None
    
    async def create_game(self, game_name: str) -> Optional[dict]:
        """Create a new game."""
        response = await self.send_and_wait({
            "type": MessageType.CREATE_GAME.value,
            "data": {
                "game_name": game_name,
                "player_name": self._player_name,
            }
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            self._current_game_id = response.get("data", {}).get("game_id")
            return response.get("data")
        return None
    
    async def join_game(self, game_id: str) -> Optional[dict]:
        """Join an existing game."""
        response = await self.send_and_wait({
            "type": MessageType.JOIN_GAME.value,
            "data": {
                "game_id": game_id,
                "player_name": self._player_name,
            }
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            self._current_game_id = game_id
            return response.get("data")
        return None
    
    async def leave_game(self) -> bool:
        """Leave the current game."""
        response = await self.send_and_wait({
            "type": MessageType.LEAVE_GAME.value,
            "data": {}
        })
        if response and response.get("data", {}).get("success"):
            self._current_game_id = None
            return True
        return False
    
    async def start_game(self) -> Optional[dict]:
        """Start the current game (host only)."""
        response = await self.send_and_wait({
            "type": MessageType.START_GAME.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def roll_dice(self) -> Optional[dict]:
        """Roll the dice."""
        response = await self.send_and_wait({
            "type": MessageType.ROLL_DICE.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def buy_property(self) -> Optional[dict]:
        """Buy the property you're standing on."""
        response = await self.send_and_wait({
            "type": MessageType.BUY_PROPERTY.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def decline_property(self) -> Optional[dict]:
        """Decline to buy the property."""
        response = await self.send_and_wait({
            "type": MessageType.DECLINE_PROPERTY.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def end_turn(self) -> Optional[dict]:
        """End your turn."""
        response = await self.send_and_wait({
            "type": MessageType.END_TURN.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def build_house(self, position: int) -> Optional[dict]:
        """Build a house on a property."""
        response = await self.send_and_wait({
            "type": MessageType.BUILD_HOUSE.value,
            "data": {"position": position}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def build_hotel(self, position: int) -> Optional[dict]:
        """Build a hotel on a property."""
        response = await self.send_and_wait({
            "type": MessageType.BUILD_HOTEL.value,
            "data": {"position": position}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def sell_building(self, position: int) -> Optional[dict]:
        """Sell a building from a property."""
        response = await self.send_and_wait({
            "type": MessageType.SELL_BUILDING.value,
            "data": {"position": position}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def mortgage_property(self, position: int) -> Optional[dict]:
        """Mortgage a property."""
        response = await self.send_and_wait({
            "type": MessageType.MORTGAGE_PROPERTY.value,
            "data": {"position": position}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def unmortgage_property(self, position: int) -> Optional[dict]:
        """Unmortgage a property."""
        response = await self.send_and_wait({
            "type": MessageType.UNMORTGAGE_PROPERTY.value,
            "data": {"position": position}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def pay_bail(self) -> Optional[dict]:
        """Pay bail to get out of jail."""
        response = await self.send_and_wait({
            "type": MessageType.PAY_BAIL.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def use_jail_card(self) -> Optional[dict]:
        """Use a Get Out of Jail Free card."""
        response = await self.send_and_wait({
            "type": MessageType.USE_JAIL_CARD.value,
            "data": {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
    
    async def declare_bankruptcy(self, creditor_id: Optional[str] = None) -> Optional[dict]:
        """Declare bankruptcy."""
        response = await self.send_and_wait({
            "type": MessageType.PLAYER_BANKRUPT.value,
            "data": {"creditor_id": creditor_id} if creditor_id else {}
        })
        if response and response.get("type") == MessageType.GAME_STATE.value:
            return response.get("data")
        return None
