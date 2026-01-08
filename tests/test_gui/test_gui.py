"""
GUI visualization test for Monopoly client.

Runs the GUI with mock game state - no server required.
Uses LocalGameController for game logic.

Run from project root: python -m tests.test_gui.test_gui
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QGroupBox, QMessageBox,
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from shared.constants import BOARD_SPACES
from shared.enums import GamePhase, PlayerState, MessageType
from client.gui.styles import MAIN_STYLESHEET, PLAYER_COLORS
from client.gui.widgets import BoardWidget, PlayerPanel, ActionPanel, PropertyDialog, EventLog
from client.gui.lobby_screen import LobbyScreen
from client.gui.game_screen import GameScreen
from client.local.controller import LocalGameController


# =============================================================================
# Test Window
# =============================================================================

class GUITestWindow(QMainWindow):
    """
    Test window for visualizing the Monopoly GUI.
    
    Provides controls to manipulate game state via LocalGameController
    and see how the UI responds.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Monopoly GUI Test")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        # Use LocalGameController for real game logic
        self._controller = LocalGameController(self)
        self._setup_sample_game()
        
        self._setup_ui()
        self._connect_signals()
        self._update_display()
    
    def _setup_sample_game(self) -> None:
        """Set up a sample game for testing."""
        self._controller.create_game("Test Game")
        
        # Add players
        self._player_ids = []
        for name in ["Alice", "Bob", "Charlie"]:
            pid = self._controller.add_player(name)
            if pid:
                self._player_ids.append(pid)
        
        # Start game
        self._controller.start_game()
        
        # Simulate some game state for visual testing
        game = self._controller.game
        if game and len(game.players) >= 3:
            players = list(game.players.values())
            
            # Alice: owns brown properties with houses
            alice = players[0]
            alice.money = 1200
            alice.position = 15
            alice.add_property(1)
            alice.add_property(3)
            game.board.properties[1].owner_id = alice.id
            game.board.properties[1].houses = 3
            game.board.properties[3].owner_id = alice.id
            game.board.properties[3].houses = 2
            
            # Bob: owns railroads and utility
            bob = players[1]
            bob.money = 1100
            bob.position = 24
            bob.add_property(5)
            bob.add_property(15)
            bob.add_property(12)
            game.board.properties[5].owner_id = bob.id
            game.board.properties[15].owner_id = bob.id
            game.board.properties[12].owner_id = bob.id
            
            # Charlie: owns Park Place (mortgaged), in jail
            charlie = players[2]
            charlie.money = 200
            charlie.position = 10
            charlie.state = PlayerState.IN_JAIL
            charlie.jail_cards = 1
            charlie.add_property(37)
            game.board.properties[37].owner_id = charlie.id
            game.board.properties[37].is_mortgaged = True
            
            # Set turn state
            game.turn_number = 12
            game.phase = GamePhase.POST_ROLL
            game.last_dice_roll = game.dice.roll()
    
    def _setup_ui(self) -> None:
        """Set up the test UI."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        
        # Left: Control panel
        control_panel = self._create_control_panel()
        control_panel.setMaximumWidth(300)
        layout.addWidget(control_panel)
        
        # Right: Stacked widget with screens
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)
        
        # Lobby screen
        self._lobby_screen = LobbyScreen()
        self._stack.addWidget(self._lobby_screen)
        
        # Game screen
        self._game_screen = GameScreen()
        self._game_screen.action_requested.connect(self._on_action_requested)
        self._stack.addWidget(self._game_screen)
        
        # Start on game screen
        self._stack.setCurrentIndex(1)
    
    def _create_control_panel(self) -> QWidget:
        """Create the control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("🎮 GUI Test Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #F1C40F;")
        layout.addWidget(title)
        
        # Screen selector
        screen_group = QGroupBox("Screen")
        screen_layout = QVBoxLayout(screen_group)
        
        self._screen_combo = QComboBox()
        self._screen_combo.addItems(["Lobby Screen", "Game Screen"])
        self._screen_combo.setCurrentIndex(1)
        self._screen_combo.currentIndexChanged.connect(self._on_screen_changed)
        screen_layout.addWidget(self._screen_combo)
        
        layout.addWidget(screen_group)
        
        # Lobby controls
        self._lobby_controls = QGroupBox("Lobby Controls")
        lobby_layout = QVBoxLayout(self._lobby_controls)
        
        btn = QPushButton("Show Connect Form")
        btn.clicked.connect(lambda: self._lobby_screen.show_connect_form())
        lobby_layout.addWidget(btn)
        
        btn = QPushButton("Show Game Browser")
        btn.clicked.connect(self._show_game_browser)
        lobby_layout.addWidget(btn)
        
        btn = QPushButton("Show Waiting Room")
        btn.clicked.connect(self._show_waiting_room)
        lobby_layout.addWidget(btn)
        
        layout.addWidget(self._lobby_controls)
        self._lobby_controls.hide()
        
        # Player selector
        player_group = QGroupBox("View As Player")
        player_layout = QVBoxLayout(player_group)
        
        self._player_combo = QComboBox()
        if self._player_ids:
            game = self._controller.game
            for pid in self._player_ids:
                player = game.players.get(pid) if game else None
                name = player.name if player else pid[:8]
                self._player_combo.addItem(f"{name} ({pid[:8]}...)")
        self._player_combo.currentIndexChanged.connect(self._on_player_changed)
        player_layout.addWidget(self._player_combo)
        
        layout.addWidget(player_group)
        
        # Game phase selector
        phase_group = QGroupBox("Game Phase")
        phase_layout = QVBoxLayout(phase_group)
        
        self._phase_combo = QComboBox()
        for phase in GamePhase:
            self._phase_combo.addItem(phase.value)
        
        game = self._controller.game
        if game:
            self._phase_combo.setCurrentText(game.phase.value)
        self._phase_combo.currentTextChanged.connect(self._on_phase_changed)
        phase_layout.addWidget(self._phase_combo)
        
        layout.addWidget(phase_group)
        
        # Game actions
        action_group = QGroupBox("Simulate Actions")
        action_layout = QVBoxLayout(action_group)
        
        btn = QPushButton("🎲 Roll Dice")
        btn.clicked.connect(self._simulate_roll)
        action_layout.addWidget(btn)
        
        btn = QPushButton("➡️ End Turn")
        btn.clicked.connect(self._simulate_end_turn)
        action_layout.addWidget(btn)
        
        btn = QPushButton("💰 Add $500")
        btn.clicked.connect(self._simulate_add_money)
        action_layout.addWidget(btn)
        
        btn = QPushButton("🏠 Build House (pos 1)")
        btn.clicked.connect(lambda: self._simulate_build(1))
        action_layout.addWidget(btn)
        
        btn = QPushButton("🏨 Build Hotel (pos 1)")
        btn.clicked.connect(lambda: self._simulate_hotel(1))
        action_layout.addWidget(btn)
        
        layout.addWidget(action_group)
        
        # Event log testing
        event_group = QGroupBox("Add Events")
        event_layout = QVBoxLayout(event_group)
        
        btn = QPushButton("📜 Add Sample Events")
        btn.clicked.connect(self._add_sample_events)
        event_layout.addWidget(btn)
        
        btn = QPushButton("❌ Add Error")
        btn.clicked.connect(lambda: self._game_screen.add_error_message("Sample error message"))
        event_layout.addWidget(btn)
        
        layout.addWidget(event_group)
        
        # Reset
        reset_group = QGroupBox("Reset")
        reset_layout = QVBoxLayout(reset_group)
        
        btn = QPushButton("🔄 Reset Game")
        btn.clicked.connect(self._reset_game)
        reset_layout.addWidget(btn)
        
        layout.addWidget(reset_group)
        
        layout.addStretch()
        
        # Info
        info = QLabel("Use controls to test UI.\nUses real game engine.")
        info.setStyleSheet("color: #7F8C8D; font-size: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        return panel
    
    def _connect_signals(self) -> None:
        """Connect controller signals."""
        self._controller.game_state_changed.connect(self._on_state_changed)
        self._controller.game_event.connect(self._on_game_event)
        self._controller.error_occurred.connect(self._on_error)
    
    def _update_display(self) -> None:
        """Update the game screen with current state."""
        if not self._player_ids:
            return
        
        current_id = self._player_ids[self._player_combo.currentIndex()]
        state = self._controller.get_state(current_id)
        
        self._game_screen.set_player_id(current_id)
        self._game_screen.set_host(True)
        self._game_screen.update_game_state(state)
    
    def _on_state_changed(self, state: dict) -> None:
        """Handle state change from controller."""
        self._update_display()
    
    def _on_game_event(self, event_type: str, data: dict) -> None:
        """Handle game event."""
        self._game_screen.add_game_event(event_type, data)
    
    def _on_error(self, message: str) -> None:
        """Handle error."""
        self._game_screen.add_error_message(message)
    
    def _on_screen_changed(self, index: int) -> None:
        """Handle screen selector change."""
        self._stack.setCurrentIndex(index)
        self._lobby_controls.setVisible(index == 0)
    
    def _on_player_changed(self, index: int) -> None:
        """Handle player selector change."""
        self._update_display()
    
    def _on_phase_changed(self, phase: str) -> None:
        """Handle phase selector change."""
        game = self._controller.game
        if game:
            game.phase = GamePhase(phase)
            self._update_display()
    
    def _on_action_requested(self, action: str, data: dict) -> None:
        """Handle action from game screen."""
        self._game_screen.add_system_message(f"Action: {action} {data}")
        
        if action == "roll_dice":
            self._controller.roll_dice()
        elif action == "end_turn":
            self._controller.end_turn()
        elif action == "buy_property":
            self._controller.buy_property()
        elif action == "decline_property":
            self._controller.decline_property()
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
        elif action == "pay_bail":
            self._controller.pay_bail()
        elif action == "use_jail_card":
            self._controller.use_jail_card()
        
        # Update phase combo
        game = self._controller.game
        if game:
            self._phase_combo.setCurrentText(game.phase.value)
    
    def _show_game_browser(self) -> None:
        """Show game browser with sample games."""
        self._lobby_screen.show_game_browser()
        self._lobby_screen.update_game_list([
            {"id": "game-1", "name": "Alice's Game", "player_count": 2},
            {"id": "game-2", "name": "Fun Times", "player_count": 3},
            {"id": "game-3", "name": "Monopoly Night", "player_count": 1},
        ])
    
    def _show_waiting_room(self) -> None:
        """Show waiting room."""
        self._lobby_screen.show_waiting_room("Test Game", is_host=True)
        state = self._controller.get_state()
        self._lobby_screen.update_waiting_room(state, is_host=True)
    
    def _simulate_roll(self) -> None:
        """Simulate dice roll."""
        # Ensure we're in PRE_ROLL phase
        game = self._controller.game
        if game and game.phase != GamePhase.PRE_ROLL:
            game.phase = GamePhase.PRE_ROLL
            if game.current_player:
                game.current_player.has_rolled = False
        
        self._controller.roll_dice()
        
        if game:
            self._phase_combo.setCurrentText(game.phase.value)
    
    def _simulate_end_turn(self) -> None:
        """Simulate end turn."""
        game = self._controller.game
        if game and game.phase != GamePhase.POST_ROLL:
            game.phase = GamePhase.POST_ROLL
        
        self._controller.end_turn()
        
        if game:
            self._phase_combo.setCurrentText(game.phase.value)
    
    def _simulate_add_money(self) -> None:
        """Add money to current viewing player."""
        if not self._player_ids:
            return
        
        current_id = self._player_ids[self._player_combo.currentIndex()]
        game = self._controller.game
        if game:
            player = game.players.get(current_id)
            if player:
                player.add_money(500)
                self._game_screen.add_system_message(f"{player.name} received $500")
                self._update_display()
    
    def _simulate_build(self, position: int) -> None:
        """Build house at position."""
        self._controller.build_house(position)
    
    def _simulate_hotel(self, position: int) -> None:
        """Build hotel at position."""
        self._controller.build_hotel(position)
    
    def _add_sample_events(self) -> None:
        """Add sample events to the log."""
        events = [
            (MessageType.DICE_ROLLED.value, {
                "player_name": "Alice",
                "die1": 6, "die2": 6, "total": 12,
                "is_double": True,
                "result_message": "Landed on Park Place",
            }),
            (MessageType.PROPERTY_BOUGHT.value, {
                "player_name": "Alice",
                "property_name": "Park Place",
                "price": 350,
            }),
            (MessageType.RENT_PAID.value, {
                "payer_name": "Bob",
                "payee_name": "Alice",
                "amount": 175,
                "property_name": "Park Place",
            }),
            (MessageType.CARD_DRAWN.value, {
                "player_name": "Charlie",
                "card_type": "CHANCE",
                "card_text": "Advance to GO. Collect $200.",
            }),
            (MessageType.JAIL_STATUS.value, {
                "player_name": "Bob",
                "in_jail": True,
                "reason": "sent_to_jail",
            }),
        ]
        
        for msg_type, data in events:
            self._game_screen.add_game_event(msg_type, data)
    
    def _reset_game(self) -> None:
        """Reset to fresh game state."""
        self._game_screen.clear()
        self._player_ids.clear()
        self._player_combo.clear()
        
        self._setup_sample_game()
        
        # Update combo box
        game = self._controller.game
        if game:
            for pid in self._player_ids:
                player = game.players.get(pid)
                name = player.name if player else pid[:8]
                self._player_combo.addItem(f"{name} ({pid[:8]}...)")
            self._phase_combo.setCurrentText(game.phase.value)
        
        self._update_display()


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the GUI test."""
    print("\n" + "=" * 60)
    print(" MONOPOLY GUI TEST")
    print("=" * 60)
    print("\nThis test runs the GUI with real game engine (no server).")
    print("\nUse the control panel on the left to:")
    print("  - Switch between screens")
    print("  - Change viewing player")
    print("  - Change game phase")
    print("  - Simulate game actions")
    print("  - Test event logging")
    print("\n" + "=" * 60 + "\n")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Monopoly GUI Test")
    
    window = GUITestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
