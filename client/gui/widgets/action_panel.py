"""
Action panel widget.

Shows available actions and buttons for the current player.
"""

from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from shared.constants import BOARD_SPACES
from shared.enums import GamePhase


class DiceDisplay(QFrame):
    """Widget showing the last dice roll."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("background-color: #ECF0F1; border-radius: 8px;")
        
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._die1 = QLabel("?")
        self._die1.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self._die1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._die1.setStyleSheet("color: #2C3E50; min-width: 50px;")
        layout.addWidget(self._die1)
        
        plus = QLabel("+")
        plus.setFont(QFont("Arial", 24))
        plus.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(plus)
        
        self._die2 = QLabel("?")
        self._die2.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self._die2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._die2.setStyleSheet("color: #2C3E50; min-width: 50px;")
        layout.addWidget(self._die2)
        
        equals = QLabel("=")
        equals.setFont(QFont("Arial", 24))
        equals.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(equals)
        
        self._total = QLabel("?")
        self._total.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self._total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._total.setStyleSheet("color: #E74C3C; min-width: 50px;")
        layout.addWidget(self._total)
    
    def set_roll(self, die1: int, die2: int) -> None:
        """Update the displayed dice values."""
        self._die1.setText(str(die1))
        self._die2.setText(str(die2))
        self._total.setText(str(die1 + die2))
        
        # Highlight doubles
        if die1 == die2:
            self._total.setStyleSheet("color: #27AE60; min-width: 50px; font-weight: bold;")
        else:
            self._total.setStyleSheet("color: #E74C3C; min-width: 50px;")
    
    def clear(self) -> None:
        """Clear the display."""
        self._die1.setText("?")
        self._die2.setText("?")
        self._total.setText("?")


class ActionPanel(QWidget):
    """
    Panel with game action buttons.
    
    Shows different buttons based on game phase and player state.
    """
    
    # Signals for actions
    roll_dice = pyqtSignal()
    buy_property = pyqtSignal()
    decline_property = pyqtSignal()
    end_turn = pyqtSignal()
    pay_bail = pyqtSignal()
    use_jail_card = pyqtSignal()
    build_house = pyqtSignal(int)  # position
    build_hotel = pyqtSignal(int)  # position
    sell_building = pyqtSignal(int)  # position
    mortgage_property = pyqtSignal(int)  # position
    unmortgage_property = pyqtSignal(int)  # position
    declare_bankruptcy = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Phase indicator
        self._phase_label = QLabel("Waiting for game...")
        self._phase_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self._phase_label.setStyleSheet("color: #F1C40F;")
        self._phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._phase_label)
        
        # Dice display
        self._dice_display = DiceDisplay()
        layout.addWidget(self._dice_display)
        
        # Main action buttons
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        
        self._roll_btn = QPushButton("🎲 Roll Dice")
        self._roll_btn.setObjectName("actionButton")
        self._roll_btn.clicked.connect(self.roll_dice.emit)
        action_layout.addWidget(self._roll_btn)
        
        self._buy_btn = QPushButton("💰 Buy Property")
        self._buy_btn.setObjectName("actionButton")
        self._buy_btn.clicked.connect(self.buy_property.emit)
        action_layout.addWidget(self._buy_btn)
        
        self._decline_btn = QPushButton("❌ Decline Property")
        self._decline_btn.clicked.connect(self.decline_property.emit)
        action_layout.addWidget(self._decline_btn)
        
        self._end_turn_btn = QPushButton("✅ End Turn")
        self._end_turn_btn.setObjectName("actionButton")
        self._end_turn_btn.clicked.connect(self.end_turn.emit)
        action_layout.addWidget(self._end_turn_btn)
        
        layout.addWidget(action_group)
        
        # Jail actions
        jail_group = QGroupBox("Jail")
        jail_layout = QVBoxLayout(jail_group)
        
        self._pay_bail_btn = QPushButton("💵 Pay $50 Bail")
        self._pay_bail_btn.clicked.connect(self.pay_bail.emit)
        jail_layout.addWidget(self._pay_bail_btn)
        
        self._use_card_btn = QPushButton("🎫 Use Get Out of Jail Card")
        self._use_card_btn.clicked.connect(self.use_jail_card.emit)
        jail_layout.addWidget(self._use_card_btn)
        
        layout.addWidget(jail_group)
        self._jail_group = jail_group
        
        # Property management (shown when property selected)
        prop_group = QGroupBox("Property Management")
        prop_layout = QVBoxLayout(prop_group)
        
        self._selected_prop_label = QLabel("Click a property to manage")
        self._selected_prop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prop_layout.addWidget(self._selected_prop_label)
        
        prop_buttons = QHBoxLayout()
        
        self._build_house_btn = QPushButton("🏠 House")
        self._build_house_btn.clicked.connect(self._on_build_house)
        prop_buttons.addWidget(self._build_house_btn)
        
        self._build_hotel_btn = QPushButton("🏨 Hotel")
        self._build_hotel_btn.clicked.connect(self._on_build_hotel)
        prop_buttons.addWidget(self._build_hotel_btn)
        
        self._sell_building_btn = QPushButton("📉 Sell")
        self._sell_building_btn.clicked.connect(self._on_sell_building)
        prop_buttons.addWidget(self._sell_building_btn)
        
        prop_layout.addLayout(prop_buttons)
        
        mortgage_buttons = QHBoxLayout()
        
        self._mortgage_btn = QPushButton("🏦 Mortgage")
        self._mortgage_btn.clicked.connect(self._on_mortgage)
        mortgage_buttons.addWidget(self._mortgage_btn)
        
        self._unmortgage_btn = QPushButton("💳 Unmortgage")
        self._unmortgage_btn.clicked.connect(self._on_unmortgage)
        mortgage_buttons.addWidget(self._unmortgage_btn)
        
        prop_layout.addLayout(mortgage_buttons)
        
        layout.addWidget(prop_group)
        self._prop_group = prop_group
        
        # Bankruptcy button (always visible but usually disabled)
        self._bankruptcy_btn = QPushButton("💀 Declare Bankruptcy")
        self._bankruptcy_btn.setObjectName("dangerButton")
        self._bankruptcy_btn.clicked.connect(self.declare_bankruptcy.emit)
        layout.addWidget(self._bankruptcy_btn)
        
        layout.addStretch()
        
        # State
        self._selected_position: Optional[int] = None
        self._game_state: Optional[dict] = None
        self._player_id: Optional[str] = None
        
        # Initial state
        self._disable_all()
    
    def _disable_all(self) -> None:
        """Disable all action buttons."""
        self._roll_btn.setEnabled(False)
        self._buy_btn.setEnabled(False)
        self._decline_btn.setEnabled(False)
        self._end_turn_btn.setEnabled(False)
        self._pay_bail_btn.setEnabled(False)
        self._use_card_btn.setEnabled(False)
        self._build_house_btn.setEnabled(False)
        self._build_hotel_btn.setEnabled(False)
        self._sell_building_btn.setEnabled(False)
        self._mortgage_btn.setEnabled(False)
        self._unmortgage_btn.setEnabled(False)
        self._bankruptcy_btn.setEnabled(False)
        
        self._jail_group.hide()
        self._prop_group.hide()
    
    def set_player_id(self, player_id: str) -> None:
        """Set the current player's ID."""
        self._player_id = player_id
    
    def update_state(self, game_state: dict) -> None:
        """Update based on current game state."""
        self._game_state = game_state
        
        phase = game_state.get("phase", "WAITING")
        is_my_turn = game_state.get("is_your_turn", False)
        current_player_id = game_state.get("current_player_id")
        
        # Update phase label
        phase_text = {
            "WAITING": "⏳ Waiting for players...",
            "PRE_ROLL": "🎲 Roll the dice!",
            "POST_ROLL": "🤔 Decide your move",
            "PROPERTY_DECISION": "🏠 Buy this property?",
            "PAYING_RENT": "💸 Pay up!",
            "TRADING": "🤝 Trading",
            "BANKRUPT": "💀 Bankruptcy",
            "GAME_OVER": "🏆 Game Over!",
        }.get(phase, phase)
        
        if not is_my_turn and phase not in ("WAITING", "GAME_OVER"):
            # Find current player name
            for p in game_state.get("players", []):
                if p.get("id") == current_player_id:
                    phase_text = f"⏳ {p.get('name', 'Someone')}'s turn"
                    break
        
        self._phase_label.setText(phase_text)
        
        # Update dice display
        last_roll = game_state.get("last_dice_roll")
        if last_roll and len(last_roll) == 2:
            self._dice_display.set_roll(last_roll[0], last_roll[1])
        
        # Reset buttons
        self._disable_all()
        
        # Get my player data
        my_player = None
        for p in game_state.get("players", []):
            if p.get("id") == self._player_id:
                my_player = p
                break
        
        if not my_player:
            return
        
        my_state = my_player.get("state", "ACTIVE")
        in_jail = my_state == "IN_JAIL"
        
        # Show jail options if in jail
        if in_jail and is_my_turn:
            self._jail_group.show()
            self._pay_bail_btn.setEnabled(my_player.get("money", 0) >= 50)
            self._use_card_btn.setEnabled(my_player.get("jail_cards", 0) > 0)
        
        # Show property management if I own properties
        if my_player.get("properties"):
            self._prop_group.show()
        
        # Enable actions based on phase
        if is_my_turn:
            if phase == "PRE_ROLL":
                self._roll_btn.setEnabled(True)
            
            elif phase == "PROPERTY_DECISION":
                # Check if can afford
                position = my_player.get("position", 0)
                space = BOARD_SPACES.get(position, {})
                cost = space.get("cost", 0)
                
                self._buy_btn.setEnabled(my_player.get("money", 0) >= cost)
                self._buy_btn.setText(f"💰 Buy for ${cost}")
                self._decline_btn.setEnabled(True)
            
            elif phase == "POST_ROLL":
                self._end_turn_btn.setEnabled(True)
            
            elif phase == "PAYING_RENT":
                # Player needs to raise money - can mortgage, sell, or go bankrupt
                self._bankruptcy_btn.setEnabled(True)
        
        # Bankruptcy available if in debt
        if my_state == "ACTIVE" and phase == "PAYING_RENT":
            self._bankruptcy_btn.setEnabled(True)
        
        # Update selected property buttons
        self._update_property_buttons()
    
    def select_property(self, position: int) -> None:
        """Select a property for management."""
        self._selected_position = position
        
        space = BOARD_SPACES.get(position, {})
        name = space.get("name", f"Space {position}")
        self._selected_prop_label.setText(f"Selected: {name}")
        
        self._update_property_buttons()
    
    def _update_property_buttons(self) -> None:
        """Update property management buttons based on selection."""
        self._build_house_btn.setEnabled(False)
        self._build_hotel_btn.setEnabled(False)
        self._sell_building_btn.setEnabled(False)
        self._mortgage_btn.setEnabled(False)
        self._unmortgage_btn.setEnabled(False)
        
        if not self._game_state or self._selected_position is None:
            return
        
        # Get property data
        prop_data = self._game_state.get("board", {}).get(str(self._selected_position))
        if not prop_data:
            return
        
        # Only manage own properties
        if prop_data.get("owner_id") != self._player_id:
            self._selected_prop_label.setText("Not your property")
            return
        
        # Get player money
        my_money = 0
        for p in self._game_state.get("players", []):
            if p.get("id") == self._player_id:
                my_money = p.get("money", 0)
                break
        
        space = BOARD_SPACES.get(self._selected_position, {})
        house_cost = space.get("house_cost", 0)
        is_mortgaged = prop_data.get("is_mortgaged", False)
        houses = prop_data.get("houses", 0)
        has_hotel = prop_data.get("has_hotel", False)
        
        if is_mortgaged:
            # Can only unmortgage
            mortgage_value = space.get("cost", 0) // 2
            unmortgage_cost = int(mortgage_value * 1.1)
            self._unmortgage_btn.setEnabled(my_money >= unmortgage_cost)
            self._unmortgage_btn.setText(f"💳 Unmortgage (${unmortgage_cost})")
        else:
            # Can mortgage if no buildings
            if houses == 0 and not has_hotel:
                mortgage_value = space.get("cost", 0) // 2
                self._mortgage_btn.setEnabled(True)
                self._mortgage_btn.setText(f"🏦 Mortgage (+${mortgage_value})")
            
            # Can build if it's a color property (has house_cost)
            if house_cost:
                if has_hotel:
                    # Can sell hotel
                    self._sell_building_btn.setEnabled(True)
                elif houses == 4:
                    # Can build hotel or sell house
                    self._build_hotel_btn.setEnabled(my_money >= house_cost)
                    self._sell_building_btn.setEnabled(True)
                elif houses > 0:
                    # Can build house or sell house
                    self._build_house_btn.setEnabled(my_money >= house_cost)
                    self._sell_building_btn.setEnabled(True)
                else:
                    # Can only build house (if have monopoly - server validates)
                    self._build_house_btn.setEnabled(my_money >= house_cost)
    
    def _on_build_house(self) -> None:
        if self._selected_position is not None:
            self.build_house.emit(self._selected_position)
    
    def _on_build_hotel(self) -> None:
        if self._selected_position is not None:
            self.build_hotel.emit(self._selected_position)
    
    def _on_sell_building(self) -> None:
        if self._selected_position is not None:
            self.sell_building.emit(self._selected_position)
    
    def _on_mortgage(self) -> None:
        if self._selected_position is not None:
            self.mortgage_property.emit(self._selected_position)
    
    def _on_unmortgage(self) -> None:
        if self._selected_position is not None:
            self.unmortgage_property.emit(self._selected_position)
    
    def clear(self) -> None:
        """Reset the panel."""
        self._disable_all()
        self._dice_display.clear()
        self._phase_label.setText("Waiting for game...")
        self._selected_position = None
        self._game_state = None
