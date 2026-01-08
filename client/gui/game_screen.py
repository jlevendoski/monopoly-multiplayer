"""
Main game screen showing the board and controls.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMessageBox, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal

from client.gui.widgets import (
    BoardWidget, PlayerPanel, ActionPanel, 
    PropertyDialog, EventLog
)


class GameScreen(QWidget):
    """
    Main game screen with board, player info, and action controls.
    
    Signals:
        action_requested: An action was requested (action_type, data)
        leave_game_requested: Player wants to leave
    """
    
    action_requested = pyqtSignal(str, dict)  # action_type, data
    leave_game_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._player_id: Optional[str] = None
        self._game_state: Optional[dict] = None
        self._is_host: bool = False
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Players
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self._player_panel = PlayerPanel()
        left_layout.addWidget(self._player_panel)
        
        # Leave game button
        leave_btn = QPushButton("Leave Game")
        leave_btn.setObjectName("dangerButton")
        leave_btn.clicked.connect(self._on_leave_game)
        left_layout.addWidget(leave_btn)
        
        left_panel.setMaximumWidth(280)
        splitter.addWidget(left_panel)
        
        # Center - Board
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        self._board = BoardWidget()
        center_layout.addWidget(self._board, 1)
        
        splitter.addWidget(center_panel)
        
        # Right panel - Actions and Log
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self._action_panel = ActionPanel()
        right_layout.addWidget(self._action_panel)
        
        self._event_log = EventLog()
        right_layout.addWidget(self._event_log, 1)
        
        right_panel.setMaximumWidth(320)
        splitter.addWidget(right_panel)
        
        # Set stretch factors
        splitter.setStretchFactor(0, 0)  # Left panel - fixed
        splitter.setStretchFactor(1, 1)  # Center - stretches
        splitter.setStretchFactor(2, 0)  # Right panel - fixed
        
        layout.addWidget(splitter)
    
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Board clicks
        self._board.space_clicked.connect(self._on_space_clicked)
        
        # Action panel signals
        self._action_panel.roll_dice.connect(
            lambda: self.action_requested.emit("roll_dice", {})
        )
        self._action_panel.buy_property.connect(
            lambda: self.action_requested.emit("buy_property", {})
        )
        self._action_panel.decline_property.connect(
            lambda: self.action_requested.emit("decline_property", {})
        )
        self._action_panel.end_turn.connect(
            lambda: self.action_requested.emit("end_turn", {})
        )
        self._action_panel.pay_bail.connect(
            lambda: self.action_requested.emit("pay_bail", {})
        )
        self._action_panel.use_jail_card.connect(
            lambda: self.action_requested.emit("use_jail_card", {})
        )
        self._action_panel.build_house.connect(
            lambda pos: self.action_requested.emit("build_house", {"position": pos})
        )
        self._action_panel.build_hotel.connect(
            lambda pos: self.action_requested.emit("build_hotel", {"position": pos})
        )
        self._action_panel.sell_building.connect(
            lambda pos: self.action_requested.emit("sell_building", {"position": pos})
        )
        self._action_panel.mortgage_property.connect(
            lambda pos: self.action_requested.emit("mortgage_property", {"position": pos})
        )
        self._action_panel.unmortgage_property.connect(
            lambda pos: self.action_requested.emit("unmortgage_property", {"position": pos})
        )
        self._action_panel.declare_bankruptcy.connect(
            lambda: self.action_requested.emit("declare_bankruptcy", {})
        )
    
    def _on_space_clicked(self, position: int) -> None:
        """Handle click on a board space."""
        if not self._game_state:
            return
        
        # Select property for management
        self._action_panel.select_property(position)
        
        # Show property dialog on double-click behavior (single click selects)
        # For now, just select. Could add double-click for dialog.
    
    def _on_leave_game(self) -> None:
        """Handle leave game button."""
        result = QMessageBox.question(
            self,
            "Leave Game",
            "Are you sure you want to leave the game?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.Yes:
            self.leave_game_requested.emit()
    
    def set_player_id(self, player_id: str) -> None:
        """Set the current player's ID."""
        self._player_id = player_id
        self._player_panel.set_player_id(player_id)
        self._action_panel.set_player_id(player_id)
    
    def set_host(self, is_host: bool) -> None:
        """Set whether this player is the host."""
        self._is_host = is_host
    
    def update_game_state(self, state: dict) -> None:
        """Update with new game state."""
        self._game_state = state
        
        # Update all widgets
        self._board.set_game_state(state, self._player_id)
        self._player_panel.update_players(state)
        self._action_panel.update_state(state)
    
    def add_game_event(self, msg_type: str, data: dict) -> None:
        """Add a game event to the log."""
        self._event_log.add_game_event(msg_type, data)
    
    def add_system_message(self, message: str) -> None:
        """Add a system message to the log."""
        self._event_log.add_system_message(message)
    
    def add_error_message(self, message: str) -> None:
        """Add an error message to the log."""
        self._event_log.add_error_message(message)
    
    def show_property_dialog(self, position: int) -> None:
        """Show the property detail dialog."""
        if self._game_state:
            dialog = PropertyDialog(position, self._game_state, self)
            dialog.exec()
    
    def clear(self) -> None:
        """Reset the screen."""
        self._board.clear()
        self._player_panel.clear()
        self._action_panel.clear()
        self._event_log.clear()
        self._game_state = None
