"""
Board representation and property management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.constants import (
    BOARD_SIZE, BOARD_SPACES, PROPERTY_GROUPS,
    UTILITY_MULTIPLIERS
)
from shared.enums import SpaceType, PropertyGroup


@dataclass
class Property:
    """Represents a purchasable property on the board."""
    
    position: int
    name: str
    space_type: SpaceType
    cost: int
    group: str
    rents: List[int] | None  # Base rent through hotel
    house_cost: int | None
    
    # Ownership and development
    owner_id: str | None = None
    houses: int = 0
    has_hotel: bool = False
    is_mortgaged: bool = False
    
    @property
    def is_owned(self) -> bool:
        """Check if property is owned."""
        return self.owner_id is not None
    
    @property
    def can_be_developed(self) -> bool:
        """Check if property can have houses/hotels built."""
        return (
            self.space_type == SpaceType.PROPERTY
            and not self.is_mortgaged
            and self.house_cost is not None
        )
    
    @property
    def development_level(self) -> int:
        """
        Get development level.
        0 = undeveloped, 1-4 = houses, 5 = hotel
        """
        if self.has_hotel:
            return 5
        return self.houses
    
    @property
    def mortgage_value(self) -> int:
        """Get mortgage value (half of purchase price)."""
        return self.cost // 2
    
    @property
    def unmortgage_cost(self) -> int:
        """Get cost to unmortgage (mortgage value + 10%)."""
        return int(self.mortgage_value * 1.1)
    
    def calculate_rent(
        self, 
        dice_roll: int = 0,
        same_group_owned: int = 1,
        has_monopoly: bool = False
    ) -> int:
        """
        Calculate rent owed when landing on this property.
        
        Args:
            dice_roll: Sum of dice (for utilities)
            same_group_owned: Number of railroads/utilities owned by same player
            has_monopoly: Whether owner has monopoly (for undeveloped properties)
            
        Returns:
            Rent amount owed
        """
        if self.is_mortgaged or not self.is_owned:
            return 0
        
        if self.space_type == SpaceType.PROPERTY:
            if self.has_hotel:
                return self.rents[5]
            elif self.houses > 0:
                return self.rents[self.houses]
            elif has_monopoly:
                return self.rents[0] * 2  # Double rent for monopoly
            else:
                return self.rents[0]
        
        elif self.space_type == SpaceType.RAILROAD:
            # Rent based on number of railroads owned
            if 1 <= same_group_owned <= 4:
                return self.rents[same_group_owned - 1]
            return self.rents[0]
        
        elif self.space_type == SpaceType.UTILITY:
            multiplier = UTILITY_MULTIPLIERS.get(same_group_owned, 4)
            return dice_roll * multiplier
        
        return 0
    
    def build_house(self) -> bool:
        """
        Build a house on this property.
        
        Returns:
            True if successful
        """
        if not self.can_be_developed:
            return False
        if self.houses >= 4 or self.has_hotel:
            return False
        
        self.houses += 1
        return True
    
    def build_hotel(self) -> bool:
        """
        Build a hotel (replacing 4 houses).
        
        Returns:
            True if successful
        """
        if not self.can_be_developed:
            return False
        if self.houses != 4 or self.has_hotel:
            return False
        
        self.houses = 0
        self.has_hotel = True
        return True
    
    def sell_house(self) -> int:
        """
        Sell a house from this property.
        
        Returns:
            Money received (half of house cost), 0 if no houses
        """
        if self.houses <= 0:
            return 0
        
        self.houses -= 1
        return self.house_cost // 2
    
    def sell_hotel(self) -> int:
        """
        Sell hotel (converts back to 4 houses).
        
        Returns:
            Money received (half of hotel cost)
        """
        if not self.has_hotel:
            return 0
        
        self.has_hotel = False
        self.houses = 4
        return self.house_cost // 2
    
    def mortgage(self) -> int:
        """
        Mortgage this property.
        
        Returns:
            Money received from mortgage, 0 if cannot mortgage
        """
        if self.is_mortgaged or self.houses > 0 or self.has_hotel:
            return 0
        
        self.is_mortgaged = True
        return self.mortgage_value
    
    def unmortgage(self) -> bool:
        """
        Unmortgage this property.
        
        Returns:
            True if successful
        """
        if not self.is_mortgaged:
            return False
        
        self.is_mortgaged = False
        return True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "position": self.position,
            "name": self.name,
            "space_type": self.space_type.value,
            "cost": self.cost,
            "group": self.group,
            "owner_id": self.owner_id,
            "houses": self.houses,
            "has_hotel": self.has_hotel,
            "is_mortgaged": self.is_mortgaged,
        }


@dataclass
class Board:
    """
    Represents the Monopoly game board.
    Manages all spaces and property ownership.
    """
    
    properties: Dict[int, Property] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize board with all properties."""
        self._initialize_properties()
    
    def _initialize_properties(self) -> None:
        """Create all purchasable properties from constants."""
        for position, space_data in BOARD_SPACES.items():
            if space_data["type"] in ("PROPERTY", "RAILROAD", "UTILITY"):
                self.properties[position] = Property(
                    position=position,
                    name=space_data["name"],
                    space_type=SpaceType(space_data["type"]),
                    cost=space_data["cost"],
                    group=space_data["group"],
                    rents=space_data["rents"],
                    house_cost=space_data["house_cost"],
                )
    
    def get_space(self, position: int) -> dict:
        """
        Get information about a board space.
        
        Args:
            position: Board position (0-39)
            
        Returns:
            Space data dictionary
        """
        return BOARD_SPACES.get(position, {})
    
    def get_space_type(self, position: int) -> SpaceType:
        """Get the type of space at a position."""
        space = self.get_space(position)
        return SpaceType(space.get("type", "GO"))
    
    def get_property(self, position: int) -> Property | None:
        """Get property at position, if it exists."""
        return self.properties.get(position)
    
    def get_property_owner(self, position: int) -> str | None:
        """Get owner ID of property at position."""
        prop = self.get_property(position)
        return prop.owner_id if prop else None
    
    def is_property_available(self, position: int) -> bool:
        """Check if property at position can be purchased."""
        prop = self.get_property(position)
        return prop is not None and not prop.is_owned
    
    def get_player_properties(self, player_id: str) -> List[Property]:
        """Get all properties owned by a player."""
        return [
            prop for prop in self.properties.values()
            if prop.owner_id == player_id
        ]
    
    def get_group_properties(self, group: str) -> List[Property]:
        """Get all properties in a color group."""
        return [
            prop for prop in self.properties.values()
            if prop.group == group
        ]
    
    def player_has_monopoly(self, player_id: str, group: str) -> bool:
        """Check if player owns all properties in a group."""
        if group in ("RAILROAD", "UTILITY"):
            return False  # No monopoly for these
        
        group_properties = self.get_group_properties(group)
        if not group_properties:
            return False
        
        return all(prop.owner_id == player_id for prop in group_properties)
    
    def count_group_owned(self, player_id: str, group: str) -> int:
        """Count how many properties in a group a player owns."""
        return sum(
            1 for prop in self.get_group_properties(group)
            if prop.owner_id == player_id
        )
    
    def can_build_house(self, position: int, player_id: str) -> bool:
        """
        Check if a house can be built on a property.
        
        Validates:
        - Property exists and is owned by player
        - Player has monopoly
        - Not mortgaged
        - Even building rule (can't be more than 1 house ahead of others in group)
        - Less than 4 houses
        """
        prop = self.get_property(position)
        if not prop or prop.owner_id != player_id:
            return False
        
        if not prop.can_be_developed:
            return False
        
        if prop.houses >= 4 or prop.has_hotel:
            return False
        
        if not self.player_has_monopoly(player_id, prop.group):
            return False
        
        # Even building rule
        group_props = self.get_group_properties(prop.group)
        min_houses = min(p.development_level for p in group_props)
        
        return prop.development_level <= min_houses
    
    def can_build_hotel(self, position: int, player_id: str) -> bool:
        """
        Check if a hotel can be built on a property.
        
        Validates:
        - All monopoly requirements
        - Property has 4 houses
        - Even building rule
        """
        prop = self.get_property(position)
        if not prop or prop.owner_id != player_id:
            return False
        
        if not prop.can_be_developed:
            return False
        
        if prop.houses != 4 or prop.has_hotel:
            return False
        
        if not self.player_has_monopoly(player_id, prop.group):
            return False
        
        # Even building rule - all others must have 4 houses
        group_props = self.get_group_properties(prop.group)
        return all(p.houses >= 4 or p.has_hotel for p in group_props)
    
    def calculate_rent(
        self, 
        position: int, 
        dice_roll: int = 0,
        landing_player_id: str | None = None
    ) -> int:
        """
        Calculate rent for landing on a property.
        
        Args:
            position: Board position
            dice_roll: Sum of dice (for utilities)
            landing_player_id: ID of player who landed (to check if they own it)
            
        Returns:
            Rent amount owed
        """
        prop = self.get_property(position)
        if not prop or not prop.is_owned:
            return 0
        
        # No rent if landing on own property
        if prop.owner_id == landing_player_id:
            return 0
        
        # Calculate based on property type
        same_group_owned = self.count_group_owned(prop.owner_id, prop.group)
        has_monopoly = self.player_has_monopoly(prop.owner_id, prop.group)
        
        return prop.calculate_rent(
            dice_roll=dice_roll,
            same_group_owned=same_group_owned,
            has_monopoly=has_monopoly
        )
    
    def transfer_property(
        self, 
        position: int, 
        new_owner_id: str | None
    ) -> bool:
        """
        Transfer property ownership.
        
        Args:
            position: Property position
            new_owner_id: New owner's ID (None to remove ownership)
            
        Returns:
            True if successful
        """
        prop = self.get_property(position)
        if not prop:
            return False
        
        prop.owner_id = new_owner_id
        return True
    
    def reset(self) -> None:
        """Reset board to initial state."""
        for prop in self.properties.values():
            prop.owner_id = None
            prop.houses = 0
            prop.has_hotel = False
            prop.is_mortgaged = False
    
    def to_dict(self) -> dict:
        """Convert board state to dictionary."""
        return {
            "properties": {
                pos: prop.to_dict() 
                for pos, prop in self.properties.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Board":
        """Create board from dictionary."""
        board = cls()
        for pos_str, prop_data in data.get("properties", {}).items():
            pos = int(pos_str)
            if pos in board.properties:
                prop = board.properties[pos]
                prop.owner_id = prop_data.get("owner_id")
                prop.houses = prop_data.get("houses", 0)
                prop.has_hotel = prop_data.get("has_hotel", False)
                prop.is_mortgaged = prop_data.get("is_mortgaged", False)
        return board
