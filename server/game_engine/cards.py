"""
Chance and Community Chest card management.
"""
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Callable

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.enums import CardType


class CardAction(Enum):
    """Types of actions a card can trigger."""
    COLLECT_MONEY = auto()      # Collect from bank
    PAY_MONEY = auto()          # Pay to bank
    COLLECT_FROM_PLAYERS = auto()  # Collect from each player
    PAY_TO_PLAYERS = auto()     # Pay each player
    MOVE_TO = auto()            # Move to specific position
    MOVE_FORWARD = auto()       # Move forward X spaces
    MOVE_BACK = auto()          # Move backward X spaces
    GO_TO_JAIL = auto()         # Go directly to jail
    GET_OUT_OF_JAIL = auto()    # Get out of jail free card
    REPAIRS = auto()            # Pay per house/hotel


@dataclass
class Card:
    """Represents a Chance or Community Chest card."""
    
    card_type: CardType
    text: str
    action: CardAction
    value: int = 0  # Money amount or position
    per_house: int = 0  # For repairs
    per_hotel: int = 0  # For repairs
    keep: bool = False  # Get out of jail free cards are kept
    
    def to_dict(self) -> dict:
        """Convert card to dictionary."""
        return {
            "card_type": self.card_type.value,
            "text": self.text,
            "action": self.action.name,
            "value": self.value,
            "per_house": self.per_house,
            "per_hotel": self.per_hotel,
            "keep": self.keep,
        }


# Define all Chance cards
CHANCE_CARDS = [
    Card(
        CardType.CHANCE,
        "Advance to Go (Collect $200)",
        CardAction.MOVE_TO,
        value=0
    ),
    Card(
        CardType.CHANCE,
        "Advance to Illinois Avenue. If you pass Go, collect $200.",
        CardAction.MOVE_TO,
        value=24
    ),
    Card(
        CardType.CHANCE,
        "Advance to St. Charles Place. If you pass Go, collect $200.",
        CardAction.MOVE_TO,
        value=11
    ),
    Card(
        CardType.CHANCE,
        "Advance to nearest Utility. If unowned, you may buy it. If owned, throw dice and pay owner 10 times the amount thrown.",
        CardAction.MOVE_TO,
        value=-1  # Special: nearest utility
    ),
    Card(
        CardType.CHANCE,
        "Advance to nearest Railroad. If unowned, you may buy it. If owned, pay owner twice the rental.",
        CardAction.MOVE_TO,
        value=-2  # Special: nearest railroad
    ),
    Card(
        CardType.CHANCE,
        "Bank pays you dividend of $50.",
        CardAction.COLLECT_MONEY,
        value=50
    ),
    Card(
        CardType.CHANCE,
        "Get Out of Jail Free.",
        CardAction.GET_OUT_OF_JAIL,
        keep=True
    ),
    Card(
        CardType.CHANCE,
        "Go Back 3 Spaces.",
        CardAction.MOVE_BACK,
        value=3
    ),
    Card(
        CardType.CHANCE,
        "Go to Jail. Go directly to Jail, do not pass Go, do not collect $200.",
        CardAction.GO_TO_JAIL
    ),
    Card(
        CardType.CHANCE,
        "Make general repairs on all your property. For each house pay $25. For each hotel pay $100.",
        CardAction.REPAIRS,
        per_house=25,
        per_hotel=100
    ),
    Card(
        CardType.CHANCE,
        "Speeding fine $15.",
        CardAction.PAY_MONEY,
        value=15
    ),
    Card(
        CardType.CHANCE,
        "Take a trip to Reading Railroad. If you pass Go, collect $200.",
        CardAction.MOVE_TO,
        value=5
    ),
    Card(
        CardType.CHANCE,
        "You have been elected Chairman of the Board. Pay each player $50.",
        CardAction.PAY_TO_PLAYERS,
        value=50
    ),
    Card(
        CardType.CHANCE,
        "Your building loan matures. Collect $150.",
        CardAction.COLLECT_MONEY,
        value=150
    ),
    Card(
        CardType.CHANCE,
        "Advance to Boardwalk.",
        CardAction.MOVE_TO,
        value=39
    ),
    Card(
        CardType.CHANCE,
        "Advance to nearest Railroad. If unowned, you may buy it. If owned, pay owner twice the rental.",
        CardAction.MOVE_TO,
        value=-2  # Special: nearest railroad
    ),
]

# Define all Community Chest cards
COMMUNITY_CHEST_CARDS = [
    Card(
        CardType.COMMUNITY_CHEST,
        "Advance to Go (Collect $200).",
        CardAction.MOVE_TO,
        value=0
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Bank error in your favor. Collect $200.",
        CardAction.COLLECT_MONEY,
        value=200
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Doctor's fee. Pay $50.",
        CardAction.PAY_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "From sale of stock you get $50.",
        CardAction.COLLECT_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Get Out of Jail Free.",
        CardAction.GET_OUT_OF_JAIL,
        keep=True
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Go to Jail. Go directly to jail, do not pass Go, do not collect $200.",
        CardAction.GO_TO_JAIL
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Holiday fund matures. Receive $100.",
        CardAction.COLLECT_MONEY,
        value=100
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Income tax refund. Collect $20.",
        CardAction.COLLECT_MONEY,
        value=20
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "It is your birthday. Collect $10 from every player.",
        CardAction.COLLECT_FROM_PLAYERS,
        value=10
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Life insurance matures. Collect $100.",
        CardAction.COLLECT_MONEY,
        value=100
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Pay hospital fees of $100.",
        CardAction.PAY_MONEY,
        value=100
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Pay school fees of $50.",
        CardAction.PAY_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Receive $25 consultancy fee.",
        CardAction.COLLECT_MONEY,
        value=25
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "You are assessed for street repair. $40 per house. $115 per hotel.",
        CardAction.REPAIRS,
        per_house=40,
        per_hotel=115
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "You have won second prize in a beauty contest. Collect $10.",
        CardAction.COLLECT_MONEY,
        value=10
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "You inherit $100.",
        CardAction.COLLECT_MONEY,
        value=100
    ),
]


@dataclass
class CardDeck:
    """Manages a deck of cards."""
    
    card_type: CardType
    cards: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    _initialized: bool = False
    
    def __post_init__(self):
        """Initialize and shuffle the deck."""
        if not self._initialized:
            self.reset()
    
    def reset(self) -> None:
        """Reset deck to initial shuffled state."""
        if self.card_type == CardType.CHANCE:
            self.cards = CHANCE_CARDS.copy()
        else:
            self.cards = COMMUNITY_CHEST_CARDS.copy()
        
        random.shuffle(self.cards)
        self.discard = []
        self._initialized = True
    
    def draw(self) -> Card:
        """
        Draw a card from the deck.
        
        Returns:
            The drawn card
        """
        if not self.cards:
            # Reshuffle discard pile
            self.cards = self.discard
            self.discard = []
            random.shuffle(self.cards)
        
        card = self.cards.pop(0)
        
        # Non-keepable cards go to discard
        if not card.keep:
            self.discard.append(card)
        
        return card
    
    def return_card(self, card: Card) -> None:
        """Return a kept card (Get Out of Jail Free) to the deck."""
        self.discard.append(card)
    
    def to_dict(self) -> dict:
        """Convert deck state to dictionary."""
        return {
            "card_type": self.card_type.value,
            "cards_remaining": len(self.cards),
            "discard_count": len(self.discard),
        }


@dataclass
class CardManager:
    """Manages both card decks."""
    
    chance: CardDeck = field(default_factory=lambda: CardDeck(CardType.CHANCE))
    community_chest: CardDeck = field(default_factory=lambda: CardDeck(CardType.COMMUNITY_CHEST))
    
    def draw_chance(self) -> Card:
        """Draw a Chance card."""
        return self.chance.draw()
    
    def draw_community_chest(self) -> Card:
        """Draw a Community Chest card."""
        return self.community_chest.draw()
    
    def return_jail_card(self, card_type: CardType) -> None:
        """Return a Get Out of Jail Free card to appropriate deck."""
        if card_type == CardType.CHANCE:
            self.chance.return_card(Card(
                CardType.CHANCE,
                "Get Out of Jail Free.",
                CardAction.GET_OUT_OF_JAIL,
                keep=True
            ))
        else:
            self.community_chest.return_card(Card(
                CardType.COMMUNITY_CHEST,
                "Get Out of Jail Free.",
                CardAction.GET_OUT_OF_JAIL,
                keep=True
            ))
    
    def reset(self) -> None:
        """Reset both decks."""
        self.chance.reset()
        self.community_chest.reset()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "chance": self.chance.to_dict(),
            "community_chest": self.community_chest.to_dict(),
        }
