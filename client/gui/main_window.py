"""
Main application window.

Manages screens and coordinates between network client and UI.
"""

import asyncio
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt

from client.config import settings
from client.network import NetworkClient, ConnectionState
from client.gui.lobby_screen import LobbyScreen
from client.gui.game_screen import GameScreen
from client.gui.styles import MAIN_STYLESHEET
from shared.enums import MessageType, GamePhase


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Coordinates between the network client and UI screens.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Monopoly")
        self.setMinimumSize(settings.window_width, settings.window_height)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Network client
        self._client = NetworkClient(self)
        self._connect_client_signals()
        
        # State
        self._player_name: Optional[str] = None
        self._is_host: bool = False
        self._in_game: bool = False
        
        # Set up UI
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the main UI."""
        # Central widget with stacked screens
        self._stack = QStackedWidget()
        self._stack.setObjectName("centralWidget")
        self.setCentralWidget(self._stack)
        
        # Lobby screen
        self._lobby = LobbyScreen()
        self._connect_lobby_signals()
        self._stack.addWidget(self._lobby)
        
        # Game screen
        self._game = GameScreen()
        self._connect_game_signals()
        self._stack.addWidget(self._game)
        
        # Start on lobby
        self._stack.setCurrentIndex(0)
    
    def _connect_client_signals(self) -> None:
        """Connect network client signals."""
        self._client.connection_changed.connect(self._on_connection_changed)
        self._client.message_received.connect(self._on_message_received)
        self._client.error_occurred.connect(self._on_error)
    
    def _connect_lobby_signals(self) -> None:
        """Connect lobby screen signals."""
        self._lobby.connect_requested.connect(self._on_connect_requested)
        self._lobby.create_game_requested.connect(self._on_create_game)
        self._lobby.join_game_requested.connect(self._on_join_game)
        self._lobby.refresh_requested.connect(self._on_refresh_games)
        self._lobby.start_game_requested.connect(self._on_start_game)
        self._lobby.leave_game_requested.connect(self._on_leave_game)
    
    def _connect_game_signals(self) -> None:
        """Connect game screen signals."""
        self._game.action_requested.connect(self._on_game_action)
        self._game.leave_game_requested.connect(self._on_leave_game)
    
    # =========================================================================
    # Network event handlers
    # =========================================================================
    
    def _on_connection_changed(self, state: ConnectionState) -> None:
        """Handle connection state changes."""
        if state == ConnectionState.CONNECTED:
            self._lobby.set_connecting(False)
            if not self._in_game:
                self._lobby.show_game_browser()
                # Auto-refresh game list
                self._run_async(self._refresh_games())
        
        elif state == ConnectionState.DISCONNECTED:
            self._lobby.show_connect_form()
            self._in_game = False
            self._stack.setCurrentIndex(0)
        
        elif state == ConnectionState.CONNECTING:
            self._lobby.set_connecting(True)
        
        elif state == ConnectionState.RECONNECTING:
            self._lobby.set_status("Reconnecting...")
        
        elif state == ConnectionState.FAILED:
            self._lobby.set_connecting(False)
            self._lobby.set_status("Connection failed")
    
    def _on_message_received(self, data: dict) -> None:
        """Handle messages from server."""
        msg_type = data.get("type", "")
        msg_data = data.get("data", {})
        
        # Game state updates
        if msg_type == MessageType.GAME_STATE.value:
            self._handle_game_state(msg_data)
        
        # Game started
        elif msg_type == MessageType.GAME_STARTED.value:
            self._in_game = True
            self._stack.setCurrentIndex(1)
            self._game.add_game_event(msg_type, msg_data)
        
        # Player events
        elif msg_type in (
            MessageType.JOIN_GAME.value,
            MessageType.LEAVE_GAME.value,
            MessageType.DISCONNECT.value,
            MessageType.RECONNECT.value,
        ):
            # Update lobby or game
            if self._in_game:
                self._game.add_game_event(msg_type, msg_data)
            else:
                # Refresh lobby
                self._run_async(self._refresh_waiting_room())
        
        # Game events
        elif msg_type in (
            MessageType.DICE_ROLLED.value,
            MessageType.PROPERTY_BOUGHT.value,
            MessageType.BUILDING_CHANGED.value,
            MessageType.PROPERTY_MORTGAGED.value,
            MessageType.RENT_PAID.value,
            MessageType.JAIL_STATUS.value,
            MessageType.CARD_DRAWN.value,
            MessageType.TURN_ENDED.value,
            MessageType.PLAYER_BANKRUPT.value,
            MessageType.GAME_WON.value,
        ):
            if self._in_game:
                self._game.add_game_event(msg_type, msg_data)
        
        # Kicked from game
        elif msg_type == MessageType.KICK_PLAYER.value:
            if msg_data.get("player_id") == self._client.player_id:
                self._in_game = False
                self._stack.setCurrentIndex(0)
                self._lobby.show_game_browser()
                QMessageBox.warning(self, "Kicked", "You were kicked from the game")
    
    def _on_error(self, message: str) -> None:
        """Handle error messages."""
        logger.error(f"Error: {message}")
        
        if self._in_game:
            self._game.add_error_message(message)
        else:
            self._lobby.set_status(f"Error: {message}")
    
    def _handle_game_state(self, state: dict) -> None:
        """Handle game state update."""
        phase = state.get("phase", "WAITING")
        
        if phase == "WAITING":
            # In lobby waiting room
            self._in_game = False
            self._stack.setCurrentIndex(0)
            self._lobby.show_waiting_room(
                state.get("game_name", "Game"),
                self._is_host
            )
            self._lobby.update_waiting_room(state, self._is_host)
        else:
            # In game
            self._in_game = True
            self._stack.setCurrentIndex(1)
            self._game.set_player_id(self._client.player_id)
            self._game.set_host(self._is_host)
            self._game.update_game_state(state)
    
    # =========================================================================
    # Lobby action handlers
    # =========================================================================
    
    def _on_connect_requested(self, player_name: str) -> None:
        """Handle connect request."""
        self._player_name = player_name
        self._run_async(self._connect(player_name))
    
    async def _connect(self, player_name: str) -> None:
        """Connect to server."""
        success = await self._client.connect(player_name)
        if not success:
            self._lobby.set_connecting(False)
    
    def _on_create_game(self, game_name: str) -> None:
        """Handle create game request."""
        self._run_async(self._create_game(game_name))
    
    async def _create_game(self, game_name: str) -> None:
        """Create a new game."""
        result = await self._client.create_game(game_name)
        if result:
            self._is_host = True
            self._handle_game_state(result)
    
    def _on_join_game(self, game_id: str) -> None:
        """Handle join game request."""
        self._run_async(self._join_game(game_id))
    
    async def _join_game(self, game_id: str) -> None:
        """Join an existing game."""
        result = await self._client.join_game(game_id)
        if result:
            self._is_host = False
            self._handle_game_state(result)
    
    def _on_refresh_games(self) -> None:
        """Handle refresh games request."""
        self._run_async(self._refresh_games())
    
    async def _refresh_games(self) -> None:
        """Refresh the game list."""
        games = await self._client.list_games()
        if games is not None:
            self._lobby.update_game_list(games)
    
    async def _refresh_waiting_room(self) -> None:
        """Refresh waiting room state."""
        # The server will send updated state automatically
        pass
    
    def _on_start_game(self) -> None:
        """Handle start game request."""
        self._run_async(self._start_game())
    
    async def _start_game(self) -> None:
        """Start the game."""
        result = await self._client.start_game()
        if result:
            self._in_game = True
            self._stack.setCurrentIndex(1)
            self._game.set_player_id(self._client.player_id)
            self._game.set_host(self._is_host)
            self._game.update_game_state(result)
    
    def _on_leave_game(self) -> None:
        """Handle leave game request."""
        self._run_async(self._leave_game())
    
    async def _leave_game(self) -> None:
        """Leave the current game."""
        success = await self._client.leave_game()
        if success:
            self._in_game = False
            self._is_host = False
            self._game.clear()
            self._stack.setCurrentIndex(0)
            self._lobby.show_game_browser()
            await self._refresh_games()
    
    # =========================================================================
    # Game action handlers
    # =========================================================================
    
    def _on_game_action(self, action: str, data: dict) -> None:
        """Handle game action request."""
        self._run_async(self._perform_action(action, data))
    
    async def _perform_action(self, action: str, data: dict) -> None:
        """Perform a game action."""
        result = None
        
        if action == "roll_dice":
            result = await self._client.roll_dice()
        elif action == "buy_property":
            result = await self._client.buy_property()
        elif action == "decline_property":
            result = await self._client.decline_property()
        elif action == "end_turn":
            result = await self._client.end_turn()
        elif action == "pay_bail":
            result = await self._client.pay_bail()
        elif action == "use_jail_card":
            result = await self._client.use_jail_card()
        elif action == "build_house":
            result = await self._client.build_house(data.get("position", 0))
        elif action == "build_hotel":
            result = await self._client.build_hotel(data.get("position", 0))
        elif action == "sell_building":
            result = await self._client.sell_building(data.get("position", 0))
        elif action == "mortgage_property":
            result = await self._client.mortgage_property(data.get("position", 0))
        elif action == "unmortgage_property":
            result = await self._client.unmortgage_property(data.get("position", 0))
        elif action == "declare_bankruptcy":
            result = await self._client.declare_bankruptcy()
        
        if result:
            self._game.update_game_state(result)
    
    # =========================================================================
    # Utility methods
    # =========================================================================
    
    def _run_async(self, coro) -> None:
        """Run a coroutine in the event loop."""
        asyncio.ensure_future(coro)
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        # Disconnect from server
        if self._client.is_connected:
            self._run_async(self._client.disconnect())
        event.accept()
