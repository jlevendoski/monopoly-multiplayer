"""
Rule enforcement and validation for Monopoly.
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum, auto

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.constants import (
    BOARD_SIZE, JAIL_POSITION, GO_TO_JAIL_POSITION,
    MAX_JAIL_TURNS, JAIL_BAIL, MAX_HOUSES_PER_PROPERTY,
    TOTAL_HOUSES, TOTAL_HOTELS, BOARD_SPACES
)
from shared.enums import SpaceType, PlayerState, GamePhase

from .player import Player
from .board import Board, Property
from .dice import DiceResult


class ActionResult(Enum):
    """Result of attempting an action."""
    SUCCESS = auto()
    INSUFFICIENT_FUNDS = auto()
    NOT_YOUR_TURN = auto()
    INVALID_PROPERTY = auto()
    PROPERTY_OWNED = auto()
    PROPERTY_NOT_OWNED = auto()
    NOT_OWNER = auto()
    NO_MONOPOLY = auto()
    UNEVEN_BUILDING = auto()
    MAX_DEVELOPMENT = auto()
    PROPERTY_MORTGAGED = auto()
    HAS_BUILDINGS = auto()
    NOT_IN_JAIL = auto()
    ALREADY_ROLLED = auto()
    MUST_ROLL = auto()
    INVALID_TRADE = auto()
    GAME_NOT_STARTED = auto()
    GAME_ALREADY_STARTED = auto()
    NOT_ENOUGH_PLAYERS = auto()
    TOO_MANY_PLAYERS = auto()
    PLAYER_BANKRUPT = auto()
    NO_BUILDINGS_AVAILABLE = auto()


@dataclass
class ValidationResult:
    """Result of validating an action."""
    valid: bool
    result: ActionResult
    message: str = ""
    
    @classmethod
    def success(cls, message: str = "") -> "ValidationResult":
        return cls(valid=True, result=ActionResult.SUCCESS, message=message)
    
    @classmethod
    def failure(cls, result: ActionResult, message: str = "") -> "ValidationResult":
        return cls(valid=False, result=result, message=message)


class RuleEngine:
    """
    Enforces all Monopoly rules and validates actions.
    """
    
    def __init__(self, board: Board):
        """
        Initialize rule engine.
        
        Args:
            board: The game board
        """
        self.board = board
        self.houses_available = TOTAL_HOUSES
        self.hotels_available = TOTAL_HOTELS
    
    def validate_roll_dice(
        self,
        player: Player,
        current_player_id: str,
        phase: GamePhase
    ) -> ValidationResult:
        """Validate if player can roll dice."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        if phase not in (GamePhase.PRE_ROLL, GamePhase.POST_ROLL):
            return ValidationResult.failure(
                ActionResult.GAME_NOT_STARTED,
                "Game is not in a rollable phase"
            )
        
        if player.has_rolled and player.state != PlayerState.IN_JAIL:
            # Can only roll again if doubles were rolled
            return ValidationResult.failure(
                ActionResult.ALREADY_ROLLED,
                "You have already rolled this turn"
            )
        
        return ValidationResult.success()
    
    def validate_buy_property(
        self,
        player: Player,
        position: int,
        current_player_id: str,
        phase: GamePhase
    ) -> ValidationResult:
        """Validate if player can buy property at position."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        if phase != GamePhase.PROPERTY_DECISION:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "Not in property decision phase"
            )
        
        if player.position != position:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "You are not on this property"
            )
        
        prop = self.board.get_property(position)
        if prop is None:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "This space is not a purchasable property"
            )
        
        if prop.is_owned:
            return ValidationResult.failure(
                ActionResult.PROPERTY_OWNED,
                f"{prop.name} is already owned"
            )
        
        if not player.can_afford(prop.cost):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                f"You need ${prop.cost} to buy {prop.name}"
            )
        
        return ValidationResult.success()
    
    def validate_build_house(
        self,
        player: Player,
        position: int,
        current_player_id: str
    ) -> ValidationResult:
        """Validate if player can build a house on property."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        prop = self.board.get_property(position)
        if prop is None:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "This is not a property"
            )
        
        if prop.owner_id != player.id:
            return ValidationResult.failure(
                ActionResult.NOT_OWNER,
                "You don't own this property"
            )
        
        if prop.space_type != SpaceType.PROPERTY:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "Can only build on color properties"
            )
        
        if prop.is_mortgaged:
            return ValidationResult.failure(
                ActionResult.PROPERTY_MORTGAGED,
                "Cannot build on mortgaged property"
            )
        
        if not self.board.player_has_monopoly(player.id, prop.group):
            return ValidationResult.failure(
                ActionResult.NO_MONOPOLY,
                "You need a monopoly to build"
            )
        
        # Check for mortgaged properties in the group
        group_props = self.board.get_group_properties(prop.group)
        if any(p.is_mortgaged for p in group_props):
            return ValidationResult.failure(
                ActionResult.PROPERTY_MORTGAGED,
                "Cannot build while any property in group is mortgaged"
            )
        
        if prop.has_hotel:
            return ValidationResult.failure(
                ActionResult.MAX_DEVELOPMENT,
                "Property already has a hotel"
            )
        
        if prop.houses >= MAX_HOUSES_PER_PROPERTY:
            return ValidationResult.failure(
                ActionResult.MAX_DEVELOPMENT,
                "Property has maximum houses, build a hotel instead"
            )
        
        # Even building rule
        if not self.board.can_build_house(position, player.id):
            return ValidationResult.failure(
                ActionResult.UNEVEN_BUILDING,
                "Must build evenly across all properties in group"
            )
        
        if self.houses_available <= 0:
            return ValidationResult.failure(
                ActionResult.NO_BUILDINGS_AVAILABLE,
                "No houses available in the bank"
            )
        
        if not player.can_afford(prop.house_cost):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                f"You need ${prop.house_cost} to build a house"
            )
        
        return ValidationResult.success()
    
    def validate_build_hotel(
        self,
        player: Player,
        position: int,
        current_player_id: str
    ) -> ValidationResult:
        """Validate if player can build a hotel on property."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        prop = self.board.get_property(position)
        if prop is None:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "This is not a property"
            )
        
        if prop.owner_id != player.id:
            return ValidationResult.failure(
                ActionResult.NOT_OWNER,
                "You don't own this property"
            )
        
        if prop.space_type != SpaceType.PROPERTY:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "Can only build on color properties"
            )
        
        if prop.is_mortgaged:
            return ValidationResult.failure(
                ActionResult.PROPERTY_MORTGAGED,
                "Cannot build on mortgaged property"
            )
        
        if prop.has_hotel:
            return ValidationResult.failure(
                ActionResult.MAX_DEVELOPMENT,
                "Property already has a hotel"
            )
        
        if prop.houses != MAX_HOUSES_PER_PROPERTY:
            return ValidationResult.failure(
                ActionResult.UNEVEN_BUILDING,
                "Need 4 houses before building a hotel"
            )
        
        if not self.board.can_build_hotel(position, player.id):
            return ValidationResult.failure(
                ActionResult.UNEVEN_BUILDING,
                "Must build evenly across all properties in group"
            )
        
        if self.hotels_available <= 0:
            return ValidationResult.failure(
                ActionResult.NO_BUILDINGS_AVAILABLE,
                "No hotels available in the bank"
            )
        
        if not player.can_afford(prop.house_cost):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                f"You need ${prop.house_cost} to build a hotel"
            )
        
        return ValidationResult.success()
    
    def validate_sell_house(
        self,
        player: Player,
        position: int
    ) -> ValidationResult:
        """Validate if player can sell a house from property."""
        prop = self.board.get_property(position)
        if prop is None:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "This is not a property"
            )
        
        if prop.owner_id != player.id:
            return ValidationResult.failure(
                ActionResult.NOT_OWNER,
                "You don't own this property"
            )
        
        if prop.houses <= 0 and not prop.has_hotel:
            return ValidationResult.failure(
                ActionResult.HAS_BUILDINGS,
                "No buildings to sell"
            )
        
        # Even selling rule - can't sell if it would make uneven
        if prop.houses > 0:
            group_props = self.board.get_group_properties(prop.group)
            max_houses = max(p.development_level for p in group_props)
            if prop.development_level < max_houses:
                return ValidationResult.failure(
                    ActionResult.UNEVEN_BUILDING,
                    "Must sell evenly across all properties in group"
                )
        
        return ValidationResult.success()
    
    def validate_mortgage(
        self,
        player: Player,
        position: int
    ) -> ValidationResult:
        """Validate if player can mortgage property."""
        prop = self.board.get_property(position)
        if prop is None:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "This is not a property"
            )
        
        if prop.owner_id != player.id:
            return ValidationResult.failure(
                ActionResult.NOT_OWNER,
                "You don't own this property"
            )
        
        if prop.is_mortgaged:
            return ValidationResult.failure(
                ActionResult.PROPERTY_MORTGAGED,
                "Property is already mortgaged"
            )
        
        if prop.houses > 0 or prop.has_hotel:
            return ValidationResult.failure(
                ActionResult.HAS_BUILDINGS,
                "Must sell all buildings before mortgaging"
            )
        
        return ValidationResult.success()
    
    def validate_unmortgage(
        self,
        player: Player,
        position: int
    ) -> ValidationResult:
        """Validate if player can unmortgage property."""
        prop = self.board.get_property(position)
        if prop is None:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "This is not a property"
            )
        
        if prop.owner_id != player.id:
            return ValidationResult.failure(
                ActionResult.NOT_OWNER,
                "You don't own this property"
            )
        
        if not prop.is_mortgaged:
            return ValidationResult.failure(
                ActionResult.PROPERTY_MORTGAGED,
                "Property is not mortgaged"
            )
        
        if not player.can_afford(prop.unmortgage_cost):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                f"You need ${prop.unmortgage_cost} to unmortgage"
            )
        
        return ValidationResult.success()
    
    def validate_pay_bail(
        self,
        player: Player,
        current_player_id: str
    ) -> ValidationResult:
        """Validate if player can pay bail."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        if player.state != PlayerState.IN_JAIL:
            return ValidationResult.failure(
                ActionResult.NOT_IN_JAIL,
                "You are not in jail"
            )
        
        if not player.can_afford(JAIL_BAIL):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                f"You need ${JAIL_BAIL} to pay bail"
            )
        
        return ValidationResult.success()
    
    def validate_use_jail_card(
        self,
        player: Player,
        current_player_id: str
    ) -> ValidationResult:
        """Validate if player can use Get Out of Jail Free card."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        if player.state != PlayerState.IN_JAIL:
            return ValidationResult.failure(
                ActionResult.NOT_IN_JAIL,
                "You are not in jail"
            )
        
        if player.jail_cards <= 0:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "You don't have a Get Out of Jail Free card"
            )
        
        return ValidationResult.success()
    
    def validate_end_turn(
        self,
        player: Player,
        current_player_id: str,
        phase: GamePhase
    ) -> ValidationResult:
        """Validate if player can end their turn."""
        if player.id != current_player_id:
            return ValidationResult.failure(
                ActionResult.NOT_YOUR_TURN,
                "It's not your turn"
            )
        
        if phase == GamePhase.PRE_ROLL:
            return ValidationResult.failure(
                ActionResult.MUST_ROLL,
                "You must roll the dice first"
            )
        
        if phase == GamePhase.PROPERTY_DECISION:
            return ValidationResult.failure(
                ActionResult.INVALID_PROPERTY,
                "You must decide on the property first"
            )
        
        if phase == GamePhase.PAYING_RENT:
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                "You must pay rent first"
            )
        
        return ValidationResult.success()
    
    def validate_trade(
        self,
        from_player: Player,
        to_player: Player,
        offered_money: int,
        requested_money: int,
        offered_properties: List[int],
        requested_properties: List[int],
        offered_jail_cards: int,
        requested_jail_cards: int
    ) -> ValidationResult:
        """Validate a trade proposal."""
        # Check money
        if offered_money > 0 and not from_player.can_afford(offered_money):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                "You cannot afford to offer that much money"
            )
        
        if requested_money > 0 and not to_player.can_afford(requested_money):
            return ValidationResult.failure(
                ActionResult.INSUFFICIENT_FUNDS,
                "Other player cannot afford that much money"
            )
        
        # Check property ownership
        for pos in offered_properties:
            prop = self.board.get_property(pos)
            if prop is None or prop.owner_id != from_player.id:
                return ValidationResult.failure(
                    ActionResult.NOT_OWNER,
                    f"You don't own property at position {pos}"
                )
            if prop.houses > 0 or prop.has_hotel:
                return ValidationResult.failure(
                    ActionResult.HAS_BUILDINGS,
                    "Cannot trade properties with buildings"
                )
        
        for pos in requested_properties:
            prop = self.board.get_property(pos)
            if prop is None or prop.owner_id != to_player.id:
                return ValidationResult.failure(
                    ActionResult.NOT_OWNER,
                    f"Other player doesn't own property at position {pos}"
                )
            if prop.houses > 0 or prop.has_hotel:
                return ValidationResult.failure(
                    ActionResult.HAS_BUILDINGS,
                    "Cannot trade properties with buildings"
                )
        
        # Check jail cards
        if offered_jail_cards > from_player.jail_cards:
            return ValidationResult.failure(
                ActionResult.INVALID_TRADE,
                "You don't have enough Get Out of Jail Free cards"
            )
        
        if requested_jail_cards > to_player.jail_cards:
            return ValidationResult.failure(
                ActionResult.INVALID_TRADE,
                "Other player doesn't have enough Get Out of Jail Free cards"
            )
        
        # Trade must involve something
        if (offered_money == 0 and requested_money == 0 and
            len(offered_properties) == 0 and len(requested_properties) == 0 and
            offered_jail_cards == 0 and requested_jail_cards == 0):
            return ValidationResult.failure(
                ActionResult.INVALID_TRADE,
                "Trade must involve at least one item"
            )
        
        return ValidationResult.success()
    
    def calculate_total_assets(self, player: Player) -> int:
        """
        Calculate total assets of a player.
        Includes cash, property values, and building values.
        """
        total = player.money
        
        for pos in player.properties:
            prop = self.board.get_property(pos)
            if prop:
                if prop.is_mortgaged:
                    # Mortgaged properties worth nothing additional
                    pass
                else:
                    # Can mortgage for half value
                    total += prop.mortgage_value
                
                # Buildings can be sold for half price
                if prop.house_cost:
                    total += (prop.houses * prop.house_cost) // 2
                    if prop.has_hotel:
                        total += prop.house_cost // 2
        
        return total
    
    def can_player_pay(self, player: Player, amount: int) -> bool:
        """Check if player can pay amount (potentially through selling/mortgaging)."""
        return self.calculate_total_assets(player) >= amount
    
    def use_house(self) -> bool:
        """Use a house from the bank."""
        if self.houses_available > 0:
            self.houses_available -= 1
            return True
        return False
    
    def return_house(self) -> None:
        """Return a house to the bank."""
        self.houses_available += 1
    
    def use_hotel(self) -> bool:
        """Use a hotel from the bank (returns 4 houses)."""
        if self.hotels_available > 0:
            self.hotels_available -= 1
            self.houses_available += 4  # Return the 4 houses
            return True
        return False
    
    def return_hotel(self) -> None:
        """Return a hotel to the bank (takes 4 houses)."""
        self.hotels_available += 1
        self.houses_available -= 4
    
    def get_nearest_utility(self, position: int) -> int:
        """Get position of nearest utility from given position."""
        utilities = [12, 28]  # Electric Company, Water Works
        
        for i in range(1, BOARD_SIZE):
            check_pos = (position + i) % BOARD_SIZE
            if check_pos in utilities:
                return check_pos
        
        return utilities[0]
    
    def get_nearest_railroad(self, position: int) -> int:
        """Get position of nearest railroad from given position."""
        railroads = [5, 15, 25, 35]
        
        for i in range(1, BOARD_SIZE):
            check_pos = (position + i) % BOARD_SIZE
            if check_pos in railroads:
                return check_pos
        
        return railroads[0]
    
    def to_dict(self) -> dict:
        """Convert rule engine state to dictionary."""
        return {
            "houses_available": self.houses_available,
            "hotels_available": self.hotels_available,
        }
    
    def load_state(self, data: dict) -> None:
        """Load state from dictionary."""
        self.houses_available = data.get("houses_available", TOTAL_HOUSES)
        self.hotels_available = data.get("hotels_available", TOTAL_HOTELS)
