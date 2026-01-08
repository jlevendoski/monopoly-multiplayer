"""
Main game orchestration - ties all components together.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.constants import (
    BOARD_SIZE, JAIL_POSITION, GO_TO_JAIL_POSITION,
    MAX_JAIL_TURNS, JAIL_BAIL, SALARY_AMOUNT, BOARD_SPACES
)
from shared.enums import SpaceType, PlayerState, GamePhase, CardType

from .board import Board
from .player import Player
from .dice import Dice, DiceResult
from .cards import CardManager, Card, CardAction
from .rules import RuleEngine, ValidationResult, ActionResult


@dataclass
class GameEvent:
    """Represents something that happened in the game."""
    event_type: str
    data: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Game:
    """
    Main game class that orchestrates all gameplay.
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Monopoly Game"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Game components
    board: Board = field(default_factory=Board)
    dice: Dice = field(default_factory=Dice)
    cards: CardManager = field(default_factory=CardManager)
    rules: RuleEngine = field(init=False)
    
    # Players
    players: Dict[str, Player] = field(default_factory=dict)
    player_order: List[str] = field(default_factory=list)
    current_player_index: int = 0
    
    # Game state
    phase: GamePhase = GamePhase.WAITING
    turn_number: int = 0
    last_dice_roll: Optional[DiceResult] = None
    winner_id: Optional[str] = None
    
    # Event log
    events: List[GameEvent] = field(default_factory=list)
    
    # Configuration
    min_players: int = 2
    max_players: int = 4
    
    def __post_init__(self):
        """Initialize rule engine after board is created."""
        self.rules = RuleEngine(self.board)
    
    @property
    def current_player(self) -> Optional[Player]:
        """Get the current player."""
        if not self.player_order:
            return None
        player_id = self.player_order[self.current_player_index]
        return self.players.get(player_id)
    
    @property
    def active_players(self) -> List[Player]:
        """Get all non-bankrupt players."""
        return [
            p for p in self.players.values()
            if p.state != PlayerState.BANKRUPT
        ]
    
    @property
    def is_game_over(self) -> bool:
        """Check if game is over (one player left)."""
        return len(self.active_players) <= 1 and self.phase != GamePhase.WAITING
    
    def _log_event(self, event_type: str, data: dict) -> GameEvent:
        """Log a game event."""
        event = GameEvent(event_type=event_type, data=data)
        self.events.append(event)
        return event
    
    def _advance_turn(self) -> None:
        """Move to next player's turn."""
        if not self.player_order:
            return
        
        # Find next active player
        start_index = self.current_player_index
        while True:
            self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
            
            # Check if we've gone full circle
            if self.current_player_index == start_index:
                break
            
            next_player = self.current_player
            if next_player and next_player.state != PlayerState.BANKRUPT:
                break
        
        self.turn_number += 1
        self.phase = GamePhase.PRE_ROLL
        
        if self.current_player:
            self.current_player.reset_turn()
            
            # Check jail status
            if self.current_player.state == PlayerState.IN_JAIL:
                self.current_player.jail_turns += 1
        
        self._log_event("turn_started", {
            "player_id": self.current_player.id if self.current_player else None,
            "turn_number": self.turn_number,
        })
    
    # =========== Player Management ===========
    
    def add_player(self, name: str, player_id: Optional[str] = None) -> Tuple[bool, str, Optional[Player]]:
        """
        Add a player to the game.
        
        Returns:
            Tuple of (success, message, player)
        """
        if self.phase != GamePhase.WAITING:
            return False, "Game has already started", None
        
        if len(self.players) >= self.max_players:
            return False, f"Game is full ({self.max_players} players maximum)", None
        
        player = Player(name=name)
        if player_id:
            player.id = player_id
        
        self.players[player.id] = player
        self.player_order.append(player.id)
        
        self._log_event("player_joined", {
            "player_id": player.id,
            "player_name": player.name,
        })
        
        return True, f"{name} joined the game", player
    
    def remove_player(self, player_id: str) -> Tuple[bool, str]:
        """Remove a player from the game."""
        if player_id not in self.players:
            return False, "Player not found"
        
        player = self.players[player_id]
        
        if self.phase == GamePhase.WAITING:
            # Before game starts, just remove
            del self.players[player_id]
            self.player_order.remove(player_id)
        else:
            # During game, mark as bankrupt
            self._handle_bankruptcy(player, None)
        
        self._log_event("player_left", {"player_id": player_id})
        
        return True, f"{player.name} left the game"
    
    def start_game(self) -> Tuple[bool, str]:
        """Start the game."""
        if self.phase != GamePhase.WAITING:
            return False, "Game has already started"
        
        if len(self.players) < self.min_players:
            return False, f"Need at least {self.min_players} players to start"
        
        # Randomize player order
        import random
        random.shuffle(self.player_order)
        
        self.phase = GamePhase.PRE_ROLL
        self.turn_number = 1
        
        if self.current_player:
            self.current_player.reset_turn()
        
        self._log_event("game_started", {
            "player_order": self.player_order,
        })
        
        return True, "Game started!"
    
    # =========== Dice Rolling ===========
    
    def roll_dice(self, player_id: str) -> Tuple[bool, str, Optional[DiceResult]]:
        """
        Roll dice for a player.
        
        Returns:
            Tuple of (success, message, dice_result)
        """
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found", None
        
        validation = self.rules.validate_roll_dice(
            player, 
            self.current_player.id if self.current_player else "",
            self.phase
        )
        
        if not validation.valid:
            return False, validation.message, None
        
        # Roll the dice
        result = self.dice.roll()
        self.last_dice_roll = result
        player.has_rolled = True
        
        self._log_event("dice_rolled", {
            "player_id": player_id,
            "die1": result.die1,
            "die2": result.die2,
            "total": result.total,
            "is_double": result.is_double,
        })
        
        # Handle jail
        if player.state == PlayerState.IN_JAIL:
            return self._handle_jail_roll(player, result)
        
        # Track doubles
        if result.is_double:
            player.consecutive_doubles += 1
            
            # Three doubles = go to jail
            if player.consecutive_doubles >= 3:
                player.send_to_jail()
                self.phase = GamePhase.POST_ROLL
                self._log_event("sent_to_jail", {
                    "player_id": player_id,
                    "reason": "three_doubles",
                })
                return True, "Three doubles! Go to jail!", result
        else:
            player.consecutive_doubles = 0
        
        # Move player
        return self._move_player(player, result.total, result)
    
    def _handle_jail_roll(
        self, 
        player: Player, 
        result: DiceResult
    ) -> Tuple[bool, str, DiceResult]:
        """Handle dice roll while in jail."""
        if result.is_double:
            # Doubles gets you out
            player.release_from_jail()
            self._log_event("released_from_jail", {
                "player_id": player.id,
                "reason": "rolled_doubles",
            })
            return self._move_player(player, result.total, result)
        
        if player.jail_turns >= MAX_JAIL_TURNS:
            # Must pay and get out
            if player.can_afford(JAIL_BAIL):
                player.remove_money(JAIL_BAIL)
                player.release_from_jail()
                self._log_event("released_from_jail", {
                    "player_id": player.id,
                    "reason": "forced_bail",
                    "amount": JAIL_BAIL,
                })
                return self._move_player(player, result.total, result)
            else:
                # Can't afford bail - need to mortgage/sell or go bankrupt
                self.phase = GamePhase.PAYING_RENT  # Reuse this phase for forced payment
                return True, f"Must pay ${JAIL_BAIL} bail - sell assets or go bankrupt", result
        
        # Still in jail
        self.phase = GamePhase.POST_ROLL
        return True, f"No doubles. {MAX_JAIL_TURNS - player.jail_turns} attempts remaining.", result
    
    def _move_player(
        self, 
        player: Player, 
        spaces: int,
        dice_result: DiceResult
    ) -> Tuple[bool, str, DiceResult]:
        """Move player and handle landing."""
        old_position = player.position
        passed_go = player.move_forward(spaces)
        
        if passed_go:
            self._log_event("passed_go", {
                "player_id": player.id,
                "collected": SALARY_AMOUNT,
            })
        
        self._log_event("player_moved", {
            "player_id": player.id,
            "from": old_position,
            "to": player.position,
            "spaces": spaces,
        })
        
        # Handle landing
        return self._handle_landing(player, dice_result)
    
    def _handle_landing(
        self, 
        player: Player,
        dice_result: DiceResult
    ) -> Tuple[bool, str, DiceResult]:
        """Handle what happens when player lands on a space."""
        space = self.board.get_space(player.position)
        space_type = SpaceType(space["type"])
        space_name = space["name"]
        
        if space_type == SpaceType.GO:
            self.phase = GamePhase.POST_ROLL
            return True, f"Landed on GO!", dice_result
        
        elif space_type == SpaceType.JAIL:
            self.phase = GamePhase.POST_ROLL
            return True, "Just visiting jail", dice_result
        
        elif space_type == SpaceType.FREE_PARKING:
            self.phase = GamePhase.POST_ROLL
            return True, "Free Parking - take a rest!", dice_result
        
        elif space_type == SpaceType.GO_TO_JAIL:
            player.send_to_jail()
            self.phase = GamePhase.POST_ROLL
            self._log_event("sent_to_jail", {
                "player_id": player.id,
                "reason": "landed_on_go_to_jail",
            })
            return True, "Go to Jail!", dice_result
        
        elif space_type == SpaceType.TAX:
            tax_amount = space["cost"]
            if player.can_afford(tax_amount):
                player.remove_money(tax_amount)
                self.phase = GamePhase.POST_ROLL
                self._log_event("tax_paid", {
                    "player_id": player.id,
                    "amount": tax_amount,
                })
                return True, f"Paid ${tax_amount} in taxes", dice_result
            else:
                self.phase = GamePhase.PAYING_RENT
                return True, f"Must pay ${tax_amount} in taxes", dice_result
        
        elif space_type == SpaceType.CHANCE:
            return self._handle_card(player, CardType.CHANCE, dice_result)
        
        elif space_type == SpaceType.COMMUNITY_CHEST:
            return self._handle_card(player, CardType.COMMUNITY_CHEST, dice_result)
        
        elif space_type in (SpaceType.PROPERTY, SpaceType.RAILROAD, SpaceType.UTILITY):
            return self._handle_property_landing(player, dice_result)
        
        self.phase = GamePhase.POST_ROLL
        return True, f"Landed on {space_name}", dice_result
    
    def _handle_property_landing(
        self,
        player: Player,
        dice_result: DiceResult
    ) -> Tuple[bool, str, DiceResult]:
        """Handle landing on a property space."""
        prop = self.board.get_property(player.position)
        
        if not prop:
            self.phase = GamePhase.POST_ROLL
            return True, "Unknown space", dice_result
        
        if not prop.is_owned:
            # Unowned - offer to buy
            self.phase = GamePhase.PROPERTY_DECISION
            return True, f"{prop.name} is available for ${prop.cost}", dice_result
        
        if prop.owner_id == player.id:
            # Own property
            self.phase = GamePhase.POST_ROLL
            return True, f"Welcome home to {prop.name}!", dice_result
        
        # Must pay rent
        rent = self.board.calculate_rent(
            player.position,
            dice_roll=dice_result.total,
            landing_player_id=player.id
        )
        
        if rent == 0:
            # Mortgaged property
            self.phase = GamePhase.POST_ROLL
            return True, f"{prop.name} is mortgaged - no rent due", dice_result
        
        owner = self.players.get(prop.owner_id)
        owner_name = owner.name if owner else "Unknown"
        
        if player.can_afford(rent):
            player.remove_money(rent)
            if owner:
                owner.add_money(rent)
            self.phase = GamePhase.POST_ROLL
            self._log_event("rent_paid", {
                "payer_id": player.id,
                "payee_id": prop.owner_id,
                "amount": rent,
                "property": prop.name,
            })
            return True, f"Paid ${rent} rent to {owner_name}", dice_result
        else:
            self.phase = GamePhase.PAYING_RENT
            self._log_event("rent_due", {
                "payer_id": player.id,
                "payee_id": prop.owner_id,
                "amount": rent,
                "property": prop.name,
            })
            return True, f"Owe ${rent} to {owner_name} - raise funds!", dice_result
    
    def _handle_card(
        self,
        player: Player,
        card_type: CardType,
        dice_result: DiceResult
    ) -> Tuple[bool, str, DiceResult]:
        """Handle drawing a Chance or Community Chest card."""
        if card_type == CardType.CHANCE:
            card = self.cards.draw_chance()
        else:
            card = self.cards.draw_community_chest()
        
        self._log_event("card_drawn", {
            "player_id": player.id,
            "card_type": card_type.value,
            "card_text": card.text,
        })
        
        # Execute card action
        return self._execute_card(player, card, dice_result)
    
    def _execute_card(
        self,
        player: Player,
        card: Card,
        dice_result: DiceResult
    ) -> Tuple[bool, str, DiceResult]:
        """Execute a card's action."""
        if card.action == CardAction.COLLECT_MONEY:
            player.add_money(card.value)
            self.phase = GamePhase.POST_ROLL
            return True, f"{card.text} (+${card.value})", dice_result
        
        elif card.action == CardAction.PAY_MONEY:
            if player.can_afford(card.value):
                player.remove_money(card.value)
                self.phase = GamePhase.POST_ROLL
            else:
                self.phase = GamePhase.PAYING_RENT
            return True, f"{card.text} (-${card.value})", dice_result
        
        elif card.action == CardAction.COLLECT_FROM_PLAYERS:
            total = 0
            for other in self.active_players:
                if other.id != player.id:
                    amount = min(card.value, other.money)
                    other.remove_money(amount)
                    total += amount
            player.add_money(total)
            self.phase = GamePhase.POST_ROLL
            return True, f"{card.text} (+${total})", dice_result
        
        elif card.action == CardAction.PAY_TO_PLAYERS:
            total_owed = card.value * (len(self.active_players) - 1)
            if player.can_afford(total_owed):
                player.remove_money(total_owed)
                for other in self.active_players:
                    if other.id != player.id:
                        other.add_money(card.value)
                self.phase = GamePhase.POST_ROLL
            else:
                self.phase = GamePhase.PAYING_RENT
            return True, f"{card.text} (-${total_owed})", dice_result
        
        elif card.action == CardAction.MOVE_TO:
            if card.value == -1:
                # Nearest utility
                new_pos = self.rules.get_nearest_utility(player.position)
            elif card.value == -2:
                # Nearest railroad
                new_pos = self.rules.get_nearest_railroad(player.position)
            else:
                new_pos = card.value
            
            player.move_to(new_pos)
            return self._handle_landing(player, dice_result)
        
        elif card.action == CardAction.MOVE_BACK:
            new_pos = (player.position - card.value) % BOARD_SIZE
            player.move_to(new_pos, collect_go=False)
            return self._handle_landing(player, dice_result)
        
        elif card.action == CardAction.GO_TO_JAIL:
            player.send_to_jail()
            self.phase = GamePhase.POST_ROLL
            return True, card.text, dice_result
        
        elif card.action == CardAction.GET_OUT_OF_JAIL:
            player.jail_cards += 1
            self.phase = GamePhase.POST_ROLL
            return True, f"{card.text} (Card kept)", dice_result
        
        elif card.action == CardAction.REPAIRS:
            total_cost = 0
            for pos in player.properties:
                prop = self.board.get_property(pos)
                if prop:
                    total_cost += prop.houses * card.per_house
                    if prop.has_hotel:
                        total_cost += card.per_hotel
            
            if player.can_afford(total_cost):
                player.remove_money(total_cost)
                self.phase = GamePhase.POST_ROLL
            else:
                self.phase = GamePhase.PAYING_RENT
            return True, f"{card.text} (-${total_cost})", dice_result
        
        self.phase = GamePhase.POST_ROLL
        return True, card.text, dice_result
    
    # =========== Property Actions ===========
    
    def buy_property(self, player_id: str) -> Tuple[bool, str]:
        """Buy the property the player is standing on."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_buy_property(
            player,
            player.position,
            self.current_player.id if self.current_player else "",
            self.phase
        )
        
        if not validation.valid:
            return False, validation.message
        
        prop = self.board.get_property(player.position)
        player.remove_money(prop.cost)
        prop.owner_id = player.id
        player.add_property(prop.position)
        
        self.phase = GamePhase.POST_ROLL
        
        self._log_event("property_bought", {
            "player_id": player_id,
            "property": prop.name,
            "position": prop.position,
            "price": prop.cost,
        })
        
        return True, f"Bought {prop.name} for ${prop.cost}"
    
    def decline_property(self, player_id: str) -> Tuple[bool, str]:
        """Decline to buy property (would trigger auction in full rules)."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        if self.phase != GamePhase.PROPERTY_DECISION:
            return False, "Not in property decision phase"
        
        if player.id != (self.current_player.id if self.current_player else ""):
            return False, "Not your turn"
        
        prop = self.board.get_property(player.position)
        
        # House rules: no auction, property stays unowned
        self.phase = GamePhase.POST_ROLL
        
        self._log_event("property_declined", {
            "player_id": player_id,
            "property": prop.name if prop else "Unknown",
            "position": player.position,
        })
        
        return True, f"Declined to buy {prop.name if prop else 'property'}"
    
    def build_house(self, player_id: str, position: int) -> Tuple[bool, str]:
        """Build a house on a property."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_build_house(
            player,
            position,
            self.current_player.id if self.current_player else ""
        )
        
        if not validation.valid:
            return False, validation.message
        
        prop = self.board.get_property(position)
        player.remove_money(prop.house_cost)
        prop.build_house()
        self.rules.use_house()
        
        self._log_event("house_built", {
            "player_id": player_id,
            "property": prop.name,
            "position": position,
            "houses": prop.houses,
        })
        
        return True, f"Built house on {prop.name} (now {prop.houses} houses)"
    
    def build_hotel(self, player_id: str, position: int) -> Tuple[bool, str]:
        """Build a hotel on a property."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_build_hotel(
            player,
            position,
            self.current_player.id if self.current_player else ""
        )
        
        if not validation.valid:
            return False, validation.message
        
        prop = self.board.get_property(position)
        player.remove_money(prop.house_cost)
        prop.build_hotel()
        self.rules.use_hotel()
        
        self._log_event("hotel_built", {
            "player_id": player_id,
            "property": prop.name,
            "position": position,
        })
        
        return True, f"Built hotel on {prop.name}"
    
    def sell_building(self, player_id: str, position: int) -> Tuple[bool, str]:
        """Sell a house or hotel from a property."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_sell_house(player, position)
        if not validation.valid:
            return False, validation.message
        
        prop = self.board.get_property(position)
        
        if prop.has_hotel:
            refund = prop.sell_hotel()
            self.rules.return_hotel()
            building_type = "hotel"
        else:
            refund = prop.sell_house()
            self.rules.return_house()
            building_type = "house"
        
        player.add_money(refund)
        
        self._log_event("building_sold", {
            "player_id": player_id,
            "property": prop.name,
            "position": position,
            "building_type": building_type,
            "refund": refund,
        })
        
        return True, f"Sold {building_type} on {prop.name} for ${refund}"
    
    def mortgage_property(self, player_id: str, position: int) -> Tuple[bool, str]:
        """Mortgage a property."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_mortgage(player, position)
        if not validation.valid:
            return False, validation.message
        
        prop = self.board.get_property(position)
        mortgage_value = prop.mortgage()
        player.add_money(mortgage_value)
        
        self._log_event("property_mortgaged", {
            "player_id": player_id,
            "property": prop.name,
            "position": position,
            "value": mortgage_value,
        })
        
        return True, f"Mortgaged {prop.name} for ${mortgage_value}"
    
    def unmortgage_property(self, player_id: str, position: int) -> Tuple[bool, str]:
        """Unmortgage a property."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_unmortgage(player, position)
        if not validation.valid:
            return False, validation.message
        
        prop = self.board.get_property(position)
        cost = prop.unmortgage_cost
        player.remove_money(cost)
        prop.unmortgage()
        
        self._log_event("property_unmortgaged", {
            "player_id": player_id,
            "property": prop.name,
            "position": position,
            "cost": cost,
        })
        
        return True, f"Unmortgaged {prop.name} for ${cost}"
    
    # =========== Jail Actions ===========
    
    def pay_bail(self, player_id: str) -> Tuple[bool, str]:
        """Pay bail to get out of jail."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_pay_bail(
            player,
            self.current_player.id if self.current_player else ""
        )
        
        if not validation.valid:
            return False, validation.message
        
        player.remove_money(JAIL_BAIL)
        player.release_from_jail()
        
        self._log_event("bail_paid", {
            "player_id": player_id,
            "amount": JAIL_BAIL,
        })
        
        return True, f"Paid ${JAIL_BAIL} bail"
    
    def use_jail_card(self, player_id: str) -> Tuple[bool, str]:
        """Use Get Out of Jail Free card."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_use_jail_card(
            player,
            self.current_player.id if self.current_player else ""
        )
        
        if not validation.valid:
            return False, validation.message
        
        player.jail_cards -= 1
        player.release_from_jail()
        
        # Return card to deck
        self.cards.return_jail_card(CardType.CHANCE)  # Simplified
        
        self._log_event("jail_card_used", {
            "player_id": player_id,
        })
        
        return True, "Used Get Out of Jail Free card"
    
    # =========== Turn Management ===========
    
    def end_turn(self, player_id: str) -> Tuple[bool, str]:
        """End current player's turn."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        validation = self.rules.validate_end_turn(
            player,
            self.current_player.id if self.current_player else "",
            self.phase
        )
        
        if not validation.valid:
            return False, validation.message
        
        # Check for doubles (get another turn)
        if (self.last_dice_roll and 
            self.last_dice_roll.is_double and 
            player.consecutive_doubles < 3 and
            player.state != PlayerState.IN_JAIL):
            self.phase = GamePhase.PRE_ROLL
            player.has_rolled = False
            self._log_event("extra_turn", {
                "player_id": player_id,
                "reason": "doubles",
            })
            return True, "Doubles! Roll again"
        
        # Check for game over
        if self.is_game_over:
            self._end_game()
            return True, f"Game Over! {self.active_players[0].name if self.active_players else 'Nobody'} wins!"
        
        self._advance_turn()
        
        return True, f"Turn ended. {self.current_player.name}'s turn" if self.current_player else "Turn ended"
    
    def _end_game(self) -> None:
        """End the game and declare winner."""
        self.phase = GamePhase.GAME_OVER
        
        if self.active_players:
            winner = self.active_players[0]
            self.winner_id = winner.id
            self._log_event("game_over", {
                "winner_id": winner.id,
                "winner_name": winner.name,
            })
    
    # =========== Bankruptcy ===========
    
    def declare_bankruptcy(self, player_id: str, creditor_id: Optional[str] = None) -> Tuple[bool, str]:
        """Declare bankruptcy."""
        player = self.players.get(player_id)
        if not player:
            return False, "Player not found"
        
        creditor = self.players.get(creditor_id) if creditor_id else None
        self._handle_bankruptcy(player, creditor)
        
        # Check for game over
        if self.is_game_over:
            self._end_game()
            return True, f"Game Over! {self.active_players[0].name if self.active_players else 'Nobody'} wins!"
        
        # If current player went bankrupt, advance turn
        if self.current_player and self.current_player.id == player_id:
            self._advance_turn()
        
        return True, f"{player.name} declared bankruptcy"
    
    def _handle_bankruptcy(self, player: Player, creditor: Optional[Player]) -> None:
        """Handle player going bankrupt."""
        if creditor:
            # Transfer all assets to creditor
            creditor.add_money(player.money)
            creditor.jail_cards += player.jail_cards
            
            for pos in list(player.properties):
                prop = self.board.get_property(pos)
                if prop:
                    prop.owner_id = creditor.id
                    creditor.add_property(pos)
        else:
            # Return properties to bank
            for pos in list(player.properties):
                prop = self.board.get_property(pos)
                if prop:
                    # Sell all buildings
                    while prop.has_hotel:
                        prop.sell_hotel()
                        self.rules.return_hotel()
                    while prop.houses > 0:
                        prop.sell_house()
                        self.rules.return_house()
                    
                    prop.owner_id = None
                    prop.is_mortgaged = False
        
        player.declare_bankruptcy()
        
        self._log_event("bankruptcy", {
            "player_id": player.id,
            "player_name": player.name,
            "creditor_id": creditor.id if creditor else None,
        })
    
    # =========== Serialization ===========
    
    def to_dict(self) -> dict:
        """Convert game state to dictionary for saving/transmission."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "phase": self.phase.value,
            "turn_number": self.turn_number,
            "current_player_index": self.current_player_index,
            "player_order": self.player_order,
            "winner_id": self.winner_id,
            "last_dice_roll": self.last_dice_roll.to_list() if self.last_dice_roll else None,
            "players": {
                pid: player.to_dict() 
                for pid, player in self.players.items()
            },
            "board": self.board.to_dict(),
            "rules": self.rules.to_dict(),
            "cards": self.cards.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Game":
        """Create game from dictionary."""
        game = cls(
            id=data["id"],
            name=data["name"],
        )
        
        game.created_at = datetime.fromisoformat(data["created_at"])
        game.phase = GamePhase(data["phase"])
        game.turn_number = data["turn_number"]
        game.current_player_index = data["current_player_index"]
        game.player_order = data["player_order"]
        game.winner_id = data.get("winner_id")
        
        if data.get("last_dice_roll"):
            from .dice import DiceResult
            roll = data["last_dice_roll"]
            game.last_dice_roll = DiceResult(die1=roll[0], die2=roll[1])
        
        # Load players
        for pid, pdata in data.get("players", {}).items():
            game.players[pid] = Player.from_dict(pdata)
        
        # Load board
        game.board = Board.from_dict(data.get("board", {}))
        game.rules = RuleEngine(game.board)
        game.rules.load_state(data.get("rules", {}))
        
        return game
    
    def get_state_for_player(self, player_id: str) -> dict:
        """
        Get game state formatted for a specific player.
        Hides other players' private information if needed.
        """
        return {
            "game_id": self.id,
            "game_name": self.name,
            "phase": self.phase.value,
            "turn_number": self.turn_number,
            "current_player_id": self.current_player.id if self.current_player else None,
            "is_your_turn": self.current_player and self.current_player.id == player_id,
            "last_dice_roll": self.last_dice_roll.to_list() if self.last_dice_roll else None,
            "players": [
                self.players[pid].to_dict()
                for pid in self.player_order
                if pid in self.players
            ],
            "board": {
                pos: prop.to_dict()
                for pos, prop in self.board.properties.items()
            },
            "houses_available": self.rules.houses_available,
            "hotels_available": self.rules.hotels_available,
            "winner_id": self.winner_id,
        }
