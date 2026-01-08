"""
Player state management.
"""
from dataclasses import dataclass, field
from typing import Set
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.enums import PlayerState
from shared.constants import STARTING_MONEY


@dataclass
class Player:
    """Represents a player in the game."""
    
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    money: int = STARTING_MONEY
    position: int = 0
    state: PlayerState = PlayerState.ACTIVE
    
    # Jail tracking
    jail_turns: int = 0
    jail_cards: int = 0  # Get Out of Jail Free cards
    
    # Properties owned (tracked by board position)
    properties: Set[int] = field(default_factory=set)
    
    # Connection tracking
    connection_id: str | None = None
    
    # Turn tracking
    consecutive_doubles: int = 0
    has_rolled: bool = False
    
    def add_money(self, amount: int) -> int:
        """
        Add money to player's balance.
        
        Args:
            amount: Amount to add (can be negative for payments)
            
        Returns:
            New balance
        """
        self.money += amount
        return self.money
    
    def remove_money(self, amount: int) -> bool:
        """
        Remove money from player's balance.
        
        Args:
            amount: Amount to remove
            
        Returns:
            True if successful, False if insufficient funds
        """
        if self.money >= amount:
            self.money -= amount
            return True
        return False
    
    def can_afford(self, amount: int) -> bool:
        """Check if player can afford a given amount."""
        return self.money >= amount
    
    def move_to(self, position: int, collect_go: bool = True) -> bool:
        """
        Move player to a specific position.
        
        Args:
            position: Board position (0-39)
            collect_go: Whether to collect $200 if passing GO
            
        Returns:
            True if player passed GO
        """
        from shared.constants import BOARD_SIZE, SALARY_AMOUNT
        
        passed_go = False
        if collect_go and position < self.position and self.state != PlayerState.IN_JAIL:
            # Passed GO
            self.add_money(SALARY_AMOUNT)
            passed_go = True
        
        self.position = position % BOARD_SIZE
        return passed_go
    
    def move_forward(self, spaces: int) -> bool:
        """
        Move player forward by a number of spaces.
        
        Args:
            spaces: Number of spaces to move forward
            
        Returns:
            True if player passed GO
        """
        from shared.constants import BOARD_SIZE
        
        new_position = (self.position + spaces) % BOARD_SIZE
        return self.move_to(new_position)
    
    def send_to_jail(self) -> None:
        """Send player to jail."""
        from shared.constants import JAIL_POSITION
        
        self.position = JAIL_POSITION
        self.state = PlayerState.IN_JAIL
        self.jail_turns = 0
        self.consecutive_doubles = 0
    
    def release_from_jail(self) -> None:
        """Release player from jail."""
        self.state = PlayerState.ACTIVE
        self.jail_turns = 0
    
    def add_property(self, position: int) -> None:
        """Add a property to player's ownership."""
        self.properties.add(position)
    
    def remove_property(self, position: int) -> None:
        """Remove a property from player's ownership."""
        self.properties.discard(position)
    
    def declare_bankruptcy(self) -> None:
        """Mark player as bankrupt."""
        self.state = PlayerState.BANKRUPT
        self.properties.clear()
    
    def reset_turn(self) -> None:
        """Reset turn-specific state."""
        self.has_rolled = False
        if not self.consecutive_doubles:
            self.consecutive_doubles = 0
    
    def to_dict(self) -> dict:
        """Convert player to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "money": self.money,
            "position": self.position,
            "state": self.state.value,
            "jail_turns": self.jail_turns,
            "jail_cards": self.jail_cards,
            "properties": list(self.properties),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Create player from dictionary."""
        player = cls(
            name=data["name"],
            id=data["id"],
            money=data["money"],
            position=data["position"],
            state=PlayerState(data["state"]),
            jail_turns=data["jail_turns"],
            jail_cards=data["jail_cards"],
        )
        player.properties = set(data["properties"])
        return player
