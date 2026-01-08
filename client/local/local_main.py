"""
Local (offline) Monopoly game.

Hot-seat multiplayer - players take turns on the same device.
"""

import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QGroupBox, QMessageBox, QDialog, QDialogButtonBox,
    QFormLayout, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from client.config import settings
from client.gui.styles import MAIN_STYLESHEET, PLAYER_COLORS
from client.gui.game_screen import GameScreen
from client.local.controller import LocalGameController
from shared.enums import GamePhase


# =============================================================================
# Setup Dialog
# =============================================================================

class PlayerSetupDialog(QDialog):
    """Dialog for adding players before starting the game."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Game Setup")
        self.setMinimumWidth(400)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self._players: list[str] = []
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("🎲 Local Monopoly Game")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #E74C3C;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Add 2-4 players to start")
        subtitle.setStyleSheet("color: #BDC3C7;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Add player section
        add_group = QGroupBox("Add Player")
        add_layout = QHBoxLayout(add_group)
        
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter player name...")
        self._name_input.setMaxLength(20)
        self._name_input.returnPressed.connect(self._add_player)
        add_layout.addWidget(self._name_input)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_player)
        add_layout.addWidget(add_btn)
        
        layout.addWidget(add_group)
        
        # Player list
        list_group = QGroupBox("Players")
        list_layout = QVBoxLayout(list_group)
        
        self._player_list = QListWidget()
        self._player_list.setMaximumHeight(150)
        list_layout.addWidget(self._player_list)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_player)
        list_layout.addWidget(remove_btn)
        
        layout.addWidget(list_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("Start Game")
        self._start_btn.setObjectName("actionButton")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self.accept)
        button_layout.addWidget(self._start_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Quick start hint
        hint = QLabel("💡 Tip: Add 2-4 players, then click Start Game")
        hint.setStyleSheet("color: #7F8C8D; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
    
    def _add_player(self) -> None:
        """Add a player to the list."""
        name = self._name_input.text().strip()
        
        if not name:
            return
        
        if len(self._players) >= 4:
            QMessageBox.warning(self, "Error", "Maximum 4 players allowed")
            return
        
        if name in self._players:
            QMessageBox.warning(self, "Error", "Player name already exists")
            return
        
        self._players.append(name)
        
        # Add to list with color indicator
        item = QListWidgetItem(f"  {name}")
        color = PLAYER_COLORS[len(self._players) - 1]
        item.setForeground(color)
        self._player_list.addItem(item)
        
        self._name_input.clear()
        self._name_input.setFocus()
        
        self._update_start_button()
    
    def _remove_player(self) -> None:
        """Remove the selected player."""
        row = self._player_list.currentRow()
        if row >= 0:
            self._players.pop(row)
            self._player_list.takeItem(row)
            self._update_start_button()
    
    def _update_start_button(self) -> None:
        """Enable start button if we have enough players."""
        self._start_btn.setEnabled(len(self._players) >= 2)
    
    def get_players(self) -> list[str]:
        """Get the list of player names."""
        return self._players


# =============================================================================
# Turn Transition Dialog
# =============================================================================

class TurnTransitionDialog(QDialog):
    """Dialog shown between turns for hot-seat play."""
    
    def __init__(self, player_name: str, player_index: int, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Next Turn")
        self.setFixedSize(350, 200)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Player indicator
        color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]
        
        indicator = QFrame()
        indicator.setFixedHeight(8)
        indicator.setStyleSheet(f"background-color: {color.name()}; border-radius: 4px;")
        layout.addWidget(indicator)
        
        # Message
        msg = QLabel(f"🎲 {player_name}'s Turn")
        msg.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        msg.setStyleSheet("color: white;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)
        
        hint = QLabel("Pass the device to this player")
        hint.setStyleSheet("color: #BDC3C7;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Ready button
        ready_btn = QPushButton(f"I'm {player_name} - Ready!")
        ready_btn.setObjectName("actionButton")
        ready_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        ready_btn.clicked.connect(self.accept)
        layout.addWidget(ready_btn)


# =============================================================================
# Main Local Game Window
# =============================================================================

class LocalGameWindow(QMainWindow):
    """
    Main window for local Monopoly game.
    
    Uses the same GameScreen as online play but with LocalGameController
    instead of NetworkClient.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Monopoly - Local Game")
        self.setMinimumSize(settings.window_width, settings.window_height)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Controller
        self._controller = LocalGameController(self)
        self._connect_controller_signals()
        
        # Player tracking for hot-seat
        self._player_ids: list[str] = []
        self._player_names: list[str] = []
        self._current_player_index: int = 0
        
        # Set up UI
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top bar with current player indicator
        self._top_bar = self._create_top_bar()
        layout.addWidget(self._top_bar)
        
        # Game screen
        self._game_screen = GameScreen()
        self._game_screen.action_requested.connect(self._on_action)
        self._game_screen.leave_game_requested.connect(self._on_leave_game)
        layout.addWidget(self._game_screen, 1)
    
    def _create_top_bar(self) -> QWidget:
        """Create the top bar showing current player."""
        bar = QFrame()
        bar.setStyleSheet("background-color: #1A252F; padding: 5px;")
        bar.setFixedHeight(50)
        
        layout = QHBoxLayout(bar)
        
        # Current player indicator
        self._turn_label = QLabel("🎲 Setting up game...")
        self._turn_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._turn_label.setStyleSheet("color: #F1C40F;")
        layout.addWidget(self._turn_label)
        
        layout.addStretch()
        
        # New game button
        new_game_btn = QPushButton("New Game")
        new_game_btn.clicked.connect(self._start_new_game)
        layout.addWidget(new_game_btn)
        
        return bar
    
    def _connect_controller_signals(self) -> None:
        """Connect controller signals."""
        self._controller.game_state_changed.connect(self._on_state_changed)
        self._controller.game_event.connect(self._on_game_event)
        self._controller.error_occurred.connect(self._on_error)
        self._controller.player_switched.connect(self._on_player_switched)
    
    def _on_state_changed(self, state: dict) -> None:
        """Handle game state change."""
        active_id = self._controller.active_player_id
        if active_id:
            self._game_screen.set_player_id(active_id)
            self._game_screen.update_game_state(state)
    
    def _on_game_event(self, event_type: str, data: dict) -> None:
        """Handle game event."""
        self._game_screen.add_game_event(event_type, data)
    
    def _on_error(self, message: str) -> None:
        """Handle error."""
        self._game_screen.add_error_message(message)
    
    def _on_player_switched(self, player_id: str, player_name: str) -> None:
        """Handle player turn change - show transition dialog."""
        # Update turn label
        player_index = self._player_ids.index(player_id) if player_id in self._player_ids else 0
        color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]
        
        self._turn_label.setText(f"🎲 {player_name}'s Turn")
        self._turn_label.setStyleSheet(f"color: {color.name()};")
        
        self._current_player_index = player_index
        
        # Show transition dialog for hot-seat
        if self._controller.is_game_active:
            dialog = TurnTransitionDialog(player_name, player_index, self)
            dialog.exec()
    
    def _on_action(self, action: str, data: dict) -> None:
        """Handle action from game screen."""
        if action == "roll_dice":
            self._controller.roll_dice()
        elif action == "buy_property":
            self._controller.buy_property()
        elif action == "decline_property":
            self._controller.decline_property()
        elif action == "end_turn":
            self._controller.end_turn()
        elif action == "pay_bail":
            self._controller.pay_bail()
        elif action == "use_jail_card":
            self._controller.use_jail_card()
        elif action == "build_house":
            self._controller.build_house(data.get("position", 0))
        elif action == "build_hotel":
            self._controller.build_hotel(data.get("position", 0))
        elif action == "sell_building":
            self._controller.sell_building(data.get("position", 0))
        elif action == "mortgage_property":
            self._controller.mortgage_property(data.get("position", 0))
        elif action == "unmortgage_property":
            self._controller.unmortgage_property(data.get("position", 0))
        elif action == "declare_bankruptcy":
            self._confirm_bankruptcy()
    
    def _confirm_bankruptcy(self) -> None:
        """Confirm bankruptcy declaration."""
        result = QMessageBox.warning(
            self,
            "Declare Bankruptcy",
            "Are you sure you want to declare bankruptcy?\n\nYou will be eliminated from the game.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            self._controller.declare_bankruptcy()
    
    def _on_leave_game(self) -> None:
        """Handle leave game request."""
        result = QMessageBox.question(
            self,
            "Leave Game",
            "End the current game?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            self._start_new_game()
    
    def _start_new_game(self) -> None:
        """Start a new game with player setup."""
        # Show setup dialog
        dialog = PlayerSetupDialog(self)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        player_names = dialog.get_players()
        
        if len(player_names) < 2:
            return
        
        # Clear old game
        self._game_screen.clear()
        self._player_ids.clear()
        self._player_names.clear()
        
        # Create new game
        self._controller.create_game("Local Game")
        
        # Add players
        for name in player_names:
            player_id = self._controller.add_player(name)
            if player_id:
                self._player_ids.append(player_id)
                self._player_names.append(name)
        
        # Start game
        if self._controller.start_game():
            self._game_screen.add_system_message("Game started! Good luck!")
    
    def showEvent(self, event) -> None:
        """Handle window show - prompt for game setup."""
        super().showEvent(event)
        
        # Auto-start setup on first show
        if not self._controller.game:
            # Use a timer to show dialog after window is visible
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._start_new_game)


# =============================================================================
# Entry Point
# =============================================================================

def run_local_game() -> int:
    """Run the local Monopoly game."""
    app = QApplication(sys.argv)
    app.setApplicationName("Monopoly Local")
    
    window = LocalGameWindow()
    window.show()
    
    return app.exec()


def main():
    """Main entry point."""
    print("\n" + "=" * 50)
    print(" MONOPOLY - LOCAL GAME")
    print("=" * 50)
    print("\nStarting local game mode...")
    print("Players take turns on the same device.")
    print("=" * 50 + "\n")
    
    sys.exit(run_local_game())


if __name__ == "__main__":
    main()
