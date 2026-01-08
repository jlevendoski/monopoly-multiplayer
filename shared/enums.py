"""
Enumerations used throughout the game.
"""
from enum import Enum, auto


class SpaceType(str, Enum):
    """Types of spaces on the board."""
    PROPERTY = "PROPERTY"
    RAILROAD = "RAILROAD"
    UTILITY = "UTILITY"
    GO = "GO"
    JAIL = "JAIL"
    FREE_PARKING = "FREE_PARKING"
    GO_TO_JAIL = "GO_TO_JAIL"
    TAX = "TAX"
    CHANCE = "CHANCE"
    COMMUNITY_CHEST = "COMMUNITY_CHEST"


class PropertyGroup(str, Enum):
    """Property color groups."""
    BROWN = "BROWN"
    LIGHT_BLUE = "LIGHT_BLUE"
    PINK = "PINK"
    ORANGE = "ORANGE"
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    DARK_BLUE = "DARK_BLUE"
    RAILROAD = "RAILROAD"
    UTILITY = "UTILITY"


class GamePhase(str, Enum):
    """Current phase of a player's turn."""
    WAITING = "WAITING"
    PRE_ROLL = "PRE_ROLL"
    POST_ROLL = "POST_ROLL"
    PROPERTY_DECISION = "PROPERTY_DECISION"
    TRADING = "TRADING"
    PAYING_RENT = "PAYING_RENT"
    BANKRUPT = "BANKRUPT"
    GAME_OVER = "GAME_OVER"


class PlayerState(str, Enum):
    """State of a player in the game."""
    ACTIVE = "ACTIVE"
    IN_JAIL = "IN_JAIL"
    BANKRUPT = "BANKRUPT"
    DISCONNECTED = "DISCONNECTED"


class CardType(str, Enum):
    """Types of cards in the game."""
    CHANCE = "CHANCE"
    COMMUNITY_CHEST = "COMMUNITY_CHEST"


class TradeStatus(str, Enum):
    """Status of a trade offer."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class MessageType(str, Enum):
    """Types of messages between client and server."""
    # Connection
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"
    RECONNECT = "RECONNECT"
    
    # Lobby
    CREATE_GAME = "CREATE_GAME"
    JOIN_GAME = "JOIN_GAME"
    LEAVE_GAME = "LEAVE_GAME"
    LIST_GAMES = "LIST_GAMES"
    GAME_LIST = "GAME_LIST"
    
    # Game flow
    START_GAME = "START_GAME"
    GAME_STARTED = "GAME_STARTED"
    GAME_STATE = "GAME_STATE"
    
    # Turn actions
    ROLL_DICE = "ROLL_DICE"
    DICE_ROLLED = "DICE_ROLLED"
    END_TURN = "END_TURN"
    TURN_ENDED = "TURN_ENDED"
    
    # Property actions
    BUY_PROPERTY = "BUY_PROPERTY"
    DECLINE_PROPERTY = "DECLINE_PROPERTY"
    PROPERTY_BOUGHT = "PROPERTY_BOUGHT"
    
    # Building
    BUILD_HOUSE = "BUILD_HOUSE"
    BUILD_HOTEL = "BUILD_HOTEL"
    SELL_BUILDING = "SELL_BUILDING"
    BUILDING_CHANGED = "BUILDING_CHANGED"
    
    # Trading
    PROPOSE_TRADE = "PROPOSE_TRADE"
    TRADE_PROPOSED = "TRADE_PROPOSED"
    ACCEPT_TRADE = "ACCEPT_TRADE"
    REJECT_TRADE = "REJECT_TRADE"
    CANCEL_TRADE = "CANCEL_TRADE"
    TRADE_COMPLETED = "TRADE_COMPLETED"
    
    # Money & Rent
    PAY_RENT = "PAY_RENT"
    RENT_PAID = "RENT_PAID"
    MONEY_TRANSFER = "MONEY_TRANSFER"
    
    # Jail
    PAY_BAIL = "PAY_BAIL"
    USE_JAIL_CARD = "USE_JAIL_CARD"
    JAIL_STATUS = "JAIL_STATUS"
    
    # Cards
    DRAW_CARD = "DRAW_CARD"
    CARD_DRAWN = "CARD_DRAWN"
    
    # Mortgage
    MORTGAGE_PROPERTY = "MORTGAGE_PROPERTY"
    UNMORTGAGE_PROPERTY = "UNMORTGAGE_PROPERTY"
    PROPERTY_MORTGAGED = "PROPERTY_MORTGAGED"
    
    # Game end
    PLAYER_BANKRUPT = "PLAYER_BANKRUPT"
    GAME_WON = "GAME_WON"
    
    # Host privileges
    KICK_PLAYER = "KICK_PLAYER"
    ASSIGN_BANKER = "ASSIGN_BANKER"
    TRANSFER_HOST = "TRANSFER_HOST"
    
    # Errors
    ERROR = "ERROR"
    INVALID_ACTION = "INVALID_ACTION"
