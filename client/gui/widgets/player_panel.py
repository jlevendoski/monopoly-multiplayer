"""
Player information panel widget.

Shows all players' status: money, properties, jail status, etc.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from client.gui.styles import PLAYER_COLORS, PROPERTY_COLORS
from shared.constants import BOARD_SPACES


class PlayerCard(QFrame):
    """Card showing a single player's information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Name and status row
        name_row = QHBoxLayout()
        
        self._color_indicator = QLabel()
        self._color_indicator.setFixedSize(16, 16)
        self._color_indicator.setStyleSheet("border-radius: 8px;")
        name_row.addWidget(self._color_indicator)
        
        self._name_label = QLabel()
        self._name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        name_row.addWidget(self._name_label)
        
        self._status_label = QLabel()
        self._status_label.setFont(QFont("Arial", 9))
        name_row.addWidget(self._status_label)
        
        name_row.addStretch()
        layout.addLayout(name_row)
        
        # Money
        self._money_label = QLabel()
        self._money_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._money_label.setStyleSheet("color: #27AE60;")
        layout.addWidget(self._money_label)
        
        # Position
        self._position_label = QLabel()
        self._position_label.setFont(QFont("Arial", 9))
        layout.addWidget(self._position_label)
        
        # Properties summary
        self._properties_label = QLabel()
        self._properties_label.setFont(QFont("Arial", 9))
        self._properties_label.setWordWrap(True)
        layout.addWidget(self._properties_label)
        
        # Jail cards
        self._jail_cards_label = QLabel()
        self._jail_cards_label.setFont(QFont("Arial", 9))
        layout.addWidget(self._jail_cards_label)
    
    def update_player(
        self, 
        player: dict, 
        color: QColor, 
        is_current: bool,
        is_self: bool,
        board_data: dict
    ) -> None:
        """Update with player data."""
        name = player.get("name", "Unknown")
        money = player.get("money", 0)
        position = player.get("position", 0)
        state = player.get("state", "ACTIVE")
        properties = player.get("properties", [])
        jail_cards = player.get("jail_cards", 0)
        
        # Color indicator
        self._color_indicator.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 8px;"
        )
        
        # Name with markers
        name_text = name
        if is_self:
            name_text += " (You)"
        self._name_label.setText(name_text)
        
        # Status
        status_text = ""
        if is_current:
            status_text = "🎲 Current Turn"
        elif state == "IN_JAIL":
            status_text = "🔒 In Jail"
        elif state == "BANKRUPT":
            status_text = "💀 Bankrupt"
        elif state == "DISCONNECTED":
            status_text = "📴 Disconnected"
        self._status_label.setText(status_text)
        
        # Money
        self._money_label.setText(f"${money:,}")
        
        # Position
        space_name = BOARD_SPACES.get(position, {}).get("name", f"Space {position}")
        self._position_label.setText(f"📍 {space_name}")
        
        # Properties - group by color
        if properties:
            groups = {}
            for pos in properties:
                space = BOARD_SPACES.get(pos, {})
                group = space.get("group", "Other")
                if group not in groups:
                    groups[group] = 0
                groups[group] += 1
            
            prop_text = "🏠 " + ", ".join(f"{g}: {c}" for g, c in groups.items())
        else:
            prop_text = "No properties"
        self._properties_label.setText(prop_text)
        
        # Jail cards
        if jail_cards > 0:
            self._jail_cards_label.setText(f"🎫 {jail_cards} Get Out of Jail card(s)")
            self._jail_cards_label.show()
        else:
            self._jail_cards_label.hide()
        
        # Highlight current player
        if is_current:
            self.setStyleSheet("background-color: #34495E; border: 2px solid #F1C40F;")
        elif is_self:
            self.setStyleSheet("background-color: #2C3E50; border: 2px solid #3498DB;")
        elif state == "BANKRUPT":
            self.setStyleSheet("background-color: #1A1A1A; opacity: 0.5;")
        else:
            self.setStyleSheet("background-color: #2C3E50;")


class PlayerPanel(QWidget):
    """Panel showing all players' information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Players")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        # Scrollable area for player cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setSpacing(8)
        self._container_layout.addStretch()
        
        scroll.setWidget(self._container)
        layout.addWidget(scroll)
        
        self._player_cards: list[PlayerCard] = []
        self._player_id: Optional[str] = None
    
    def set_player_id(self, player_id: str) -> None:
        """Set the current player's ID."""
        self._player_id = player_id
    
    def update_players(self, game_state: dict) -> None:
        """Update with current game state."""
        players = game_state.get("players", [])
        current_player_id = game_state.get("current_player_id")
        board_data = game_state.get("board", {})
        
        # Add/remove cards as needed
        while len(self._player_cards) < len(players):
            card = PlayerCard()
            self._container_layout.insertWidget(
                self._container_layout.count() - 1,  # Before stretch
                card
            )
            self._player_cards.append(card)
        
        while len(self._player_cards) > len(players):
            card = self._player_cards.pop()
            card.deleteLater()
        
        # Update each card
        for i, player in enumerate(players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            is_current = player.get("id") == current_player_id
            is_self = player.get("id") == self._player_id
            
            self._player_cards[i].update_player(
                player, color, is_current, is_self, board_data
            )
    
    def clear(self) -> None:
        """Clear all player cards."""
        for card in self._player_cards:
            card.deleteLater()
        self._player_cards.clear()
