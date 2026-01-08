"""
Message protocol for client-server communication.

All messages are JSON objects with a "type" field and optional "data" field.
"""

from dataclasses import dataclass, field, asdict
from typing import Any
import json

from shared.enums import MessageType


@dataclass
class Message:
    """Base message structure for all client-server communication."""
    type: MessageType
    data: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None  # Optional, for matching requests to responses
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "request_id": self.request_id,
        })
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "data": self.data,
            "request_id": self.request_id,
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Deserialize message from JSON string."""
        raw = json.loads(json_str)
        return cls.from_dict(raw)
    
    @classmethod
    def from_dict(cls, raw: dict) -> "Message":
        """Create message from dictionary."""
        return cls(
            type=MessageType(raw["type"]),
            data=raw.get("data", {}),
            request_id=raw.get("request_id"),
        )


@dataclass
class ErrorMessage(Message):
    """Error response message."""
    type: MessageType = MessageType.ERROR
    
    @classmethod
    def create(cls, message: str, code: str = "ERROR", request_id: str | None = None) -> "ErrorMessage":
        """Create an error message."""
        return cls(
            data={"message": message, "code": code},
            request_id=request_id,
        )


# =============================================================================
# Lobby Messages (Client -> Server)
# =============================================================================

@dataclass
class ListGamesRequest(Message):
    """Request list of available games."""
    type: MessageType = MessageType.LIST_GAMES
    
    @classmethod
    def create(cls, status: str | None = None, request_id: str | None = None) -> "ListGamesRequest":
        data = {}
        if status:
            data["status"] = status
        return cls(data=data, request_id=request_id)


@dataclass
class CreateGameRequest(Message):
    """Request to create a new game."""
    type: MessageType = MessageType.CREATE_GAME
    
    @classmethod
    def create(
        cls,
        game_name: str,
        player_name: str,
        settings: dict | None = None,
        request_id: str | None = None
    ) -> "CreateGameRequest":
        return cls(
            data={
                "game_name": game_name,
                "player_name": player_name,
                "settings": settings or {},
            },
            request_id=request_id,
        )


@dataclass
class JoinGameRequest(Message):
    """Request to join an existing game."""
    type: MessageType = MessageType.JOIN_GAME
    
    @classmethod
    def create(
        cls,
        game_id: str,
        player_name: str,
        request_id: str | None = None
    ) -> "JoinGameRequest":
        return cls(
            data={
                "game_id": game_id,
                "player_name": player_name,
            },
            request_id=request_id,
        )


@dataclass
class LeaveGameRequest(Message):
    """Request to leave current game."""
    type: MessageType = MessageType.LEAVE_GAME
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "LeaveGameRequest":
        return cls(request_id=request_id)


@dataclass
class StartGameRequest(Message):
    """Request to start the game (host only)."""
    type: MessageType = MessageType.START_GAME
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "StartGameRequest":
        return cls(request_id=request_id)


# =============================================================================
# Game Action Messages (Client -> Server)
# =============================================================================

@dataclass
class RollDiceRequest(Message):
    """Request to roll dice."""
    type: MessageType = MessageType.ROLL_DICE
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "RollDiceRequest":
        return cls(request_id=request_id)


@dataclass
class BuyPropertyRequest(Message):
    """Request to buy the property player is standing on."""
    type: MessageType = MessageType.BUY_PROPERTY
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "BuyPropertyRequest":
        return cls(request_id=request_id)


@dataclass
class DeclinePropertyRequest(Message):
    """Request to decline buying property."""
    type: MessageType = MessageType.DECLINE_PROPERTY
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "DeclinePropertyRequest":
        return cls(request_id=request_id)


@dataclass
class BuildHouseRequest(Message):
    """Request to build a house on a property."""
    type: MessageType = MessageType.BUILD_HOUSE
    
    @classmethod
    def create(cls, position: int, request_id: str | None = None) -> "BuildHouseRequest":
        return cls(data={"position": position}, request_id=request_id)


@dataclass
class BuildHotelRequest(Message):
    """Request to build a hotel on a property."""
    type: MessageType = MessageType.BUILD_HOTEL
    
    @classmethod
    def create(cls, position: int, request_id: str | None = None) -> "BuildHotelRequest":
        return cls(data={"position": position}, request_id=request_id)


@dataclass
class SellBuildingRequest(Message):
    """Request to sell a building from a property."""
    type: MessageType = MessageType.SELL_BUILDING
    
    @classmethod
    def create(cls, position: int, request_id: str | None = None) -> "SellBuildingRequest":
        return cls(data={"position": position}, request_id=request_id)


@dataclass
class MortgagePropertyRequest(Message):
    """Request to mortgage a property."""
    type: MessageType = MessageType.MORTGAGE_PROPERTY
    
    @classmethod
    def create(cls, position: int, request_id: str | None = None) -> "MortgagePropertyRequest":
        return cls(data={"position": position}, request_id=request_id)


@dataclass
class UnmortgagePropertyRequest(Message):
    """Request to unmortgage a property."""
    type: MessageType = MessageType.UNMORTGAGE_PROPERTY
    
    @classmethod
    def create(cls, position: int, request_id: str | None = None) -> "UnmortgagePropertyRequest":
        return cls(data={"position": position}, request_id=request_id)


@dataclass
class PayBailRequest(Message):
    """Request to pay bail to get out of jail."""
    type: MessageType = MessageType.PAY_BAIL
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "PayBailRequest":
        return cls(request_id=request_id)


@dataclass
class UseJailCardRequest(Message):
    """Request to use Get Out of Jail Free card."""
    type: MessageType = MessageType.USE_JAIL_CARD
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "UseJailCardRequest":
        return cls(request_id=request_id)


@dataclass
class EndTurnRequest(Message):
    """Request to end current turn."""
    type: MessageType = MessageType.END_TURN
    
    @classmethod
    def create(cls, request_id: str | None = None) -> "EndTurnRequest":
        return cls(request_id=request_id)


@dataclass
class DeclareBankruptcyRequest(Message):
    """Request to declare bankruptcy."""
    type: MessageType = MessageType.PLAYER_BANKRUPT
    
    @classmethod
    def create(cls, creditor_id: str | None = None, request_id: str | None = None) -> "DeclareBankruptcyRequest":
        data = {}
        if creditor_id:
            data["creditor_id"] = creditor_id
        return cls(data=data, request_id=request_id)


# =============================================================================
# Server Response/Broadcast Messages (Server -> Client)
# =============================================================================

@dataclass
class GameListResponse(Message):
    """Response containing list of available games."""
    type: MessageType = MessageType.GAME_LIST
    
    @classmethod
    def create(cls, games: list[dict], request_id: str | None = None) -> "GameListResponse":
        return cls(data={"games": games}, request_id=request_id)


@dataclass
class GameStateMessage(Message):
    """Full game state broadcast to all players."""
    type: MessageType = MessageType.GAME_STATE
    
    @classmethod
    def create(cls, game_state: dict, request_id: str | None = None) -> "GameStateMessage":
        return cls(data=game_state, request_id=request_id)


@dataclass
class GameStartedMessage(Message):
    """Broadcast when game starts."""
    type: MessageType = MessageType.GAME_STARTED
    
    @classmethod
    def create(cls, game_state: dict) -> "GameStartedMessage":
        return cls(data=game_state)


@dataclass
class DiceRolledMessage(Message):
    """Broadcast when dice are rolled."""
    type: MessageType = MessageType.DICE_ROLLED
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        die1: int,
        die2: int,
        total: int,
        is_double: bool,
        result_message: str
    ) -> "DiceRolledMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "die1": die1,
            "die2": die2,
            "total": total,
            "is_double": is_double,
            "result_message": result_message,
        })


@dataclass
class PropertyBoughtMessage(Message):
    """Broadcast when property is purchased."""
    type: MessageType = MessageType.PROPERTY_BOUGHT
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        property_name: str,
        position: int,
        price: int
    ) -> "PropertyBoughtMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "property_name": property_name,
            "position": position,
            "price": price,
        })


@dataclass
class BuildingChangedMessage(Message):
    """Broadcast when buildings are built or sold."""
    type: MessageType = MessageType.BUILDING_CHANGED
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        property_name: str,
        position: int,
        action: str,  # "built_house", "built_hotel", "sold_house", "sold_hotel"
        houses: int,
        has_hotel: bool
    ) -> "BuildingChangedMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "property_name": property_name,
            "position": position,
            "action": action,
            "houses": houses,
            "has_hotel": has_hotel,
        })


@dataclass
class PropertyMortgagedMessage(Message):
    """Broadcast when property is mortgaged or unmortgaged."""
    type: MessageType = MessageType.PROPERTY_MORTGAGED
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        property_name: str,
        position: int,
        is_mortgaged: bool,
        amount: int
    ) -> "PropertyMortgagedMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "property_name": property_name,
            "position": position,
            "is_mortgaged": is_mortgaged,
            "amount": amount,
        })


@dataclass
class RentPaidMessage(Message):
    """Broadcast when rent is paid."""
    type: MessageType = MessageType.RENT_PAID
    
    @classmethod
    def create(
        cls,
        payer_id: str,
        payer_name: str,
        payee_id: str,
        payee_name: str,
        property_name: str,
        amount: int
    ) -> "RentPaidMessage":
        return cls(data={
            "payer_id": payer_id,
            "payer_name": payer_name,
            "payee_id": payee_id,
            "payee_name": payee_name,
            "property_name": property_name,
            "amount": amount,
        })


@dataclass
class TurnEndedMessage(Message):
    """Broadcast when a turn ends."""
    type: MessageType = MessageType.TURN_ENDED
    
    @classmethod
    def create(
        cls,
        previous_player_id: str,
        previous_player_name: str,
        current_player_id: str,
        current_player_name: str,
        turn_number: int
    ) -> "TurnEndedMessage":
        return cls(data={
            "previous_player_id": previous_player_id,
            "previous_player_name": previous_player_name,
            "current_player_id": current_player_id,
            "current_player_name": current_player_name,
            "turn_number": turn_number,
        })


@dataclass
class JailStatusMessage(Message):
    """Broadcast when player's jail status changes."""
    type: MessageType = MessageType.JAIL_STATUS
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        in_jail: bool,
        reason: str  # "sent_to_jail", "paid_bail", "used_card", "rolled_doubles"
    ) -> "JailStatusMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "in_jail": in_jail,
            "reason": reason,
        })


@dataclass
class CardDrawnMessage(Message):
    """Broadcast when a card is drawn."""
    type: MessageType = MessageType.CARD_DRAWN
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        card_type: str,  # "CHANCE" or "COMMUNITY_CHEST"
        card_text: str,
        result_message: str
    ) -> "CardDrawnMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "card_type": card_type,
            "card_text": card_text,
            "result_message": result_message,
        })


@dataclass
class PlayerBankruptMessage(Message):
    """Broadcast when a player goes bankrupt."""
    type: MessageType = MessageType.PLAYER_BANKRUPT
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        creditor_id: str | None,
        creditor_name: str | None
    ) -> "PlayerBankruptMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "creditor_id": creditor_id,
            "creditor_name": creditor_name,
        })


@dataclass
class GameWonMessage(Message):
    """Broadcast when the game is won."""
    type: MessageType = MessageType.GAME_WON
    
    @classmethod
    def create(
        cls,
        winner_id: str,
        winner_name: str
    ) -> "GameWonMessage":
        return cls(data={
            "winner_id": winner_id,
            "winner_name": winner_name,
        })


@dataclass 
class PlayerJoinedMessage(Message):
    """Broadcast when a player joins the game."""
    type: MessageType = MessageType.JOIN_GAME
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        game_id: str
    ) -> "PlayerJoinedMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "game_id": game_id,
        })


@dataclass
class PlayerLeftMessage(Message):
    """Broadcast when a player leaves the game."""
    type: MessageType = MessageType.LEAVE_GAME
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str
    ) -> "PlayerLeftMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
        })


@dataclass
class PlayerKickedMessage(Message):
    """Broadcast when a player is kicked from the game."""
    type: MessageType = MessageType.KICK_PLAYER
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str,
        kicked_by: str
    ) -> "PlayerKickedMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
            "kicked_by": kicked_by,
        })


@dataclass
class HostTransferredMessage(Message):
    """Broadcast when host privileges are transferred."""
    type: MessageType = MessageType.TRANSFER_HOST
    
    @classmethod
    def create(
        cls,
        new_host_id: str,
        new_host_name: str,
        old_host_id: str
    ) -> "HostTransferredMessage":
        return cls(data={
            "new_host_id": new_host_id,
            "new_host_name": new_host_name,
            "old_host_id": old_host_id,
        })


@dataclass
class PlayerDisconnectedMessage(Message):
    """Broadcast when a player disconnects."""
    type: MessageType = MessageType.DISCONNECT
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str
    ) -> "PlayerDisconnectedMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
        })


@dataclass
class PlayerReconnectedMessage(Message):
    """Broadcast when a player reconnects."""
    type: MessageType = MessageType.RECONNECT
    
    @classmethod
    def create(
        cls,
        player_id: str,
        player_name: str
    ) -> "PlayerReconnectedMessage":
        return cls(data={
            "player_id": player_id,
            "player_name": player_name,
        })


# =============================================================================
# Game Settings
# =============================================================================

@dataclass
class GameSettings:
    """Settings for a game, configured by the host."""
    allow_spectators: bool = False
    starting_money: int = 1500
    salary_amount: int = 200
    max_players: int = 4
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "GameSettings":
        return cls(
            allow_spectators=data.get("allow_spectators", False),
            starting_money=data.get("starting_money", 1500),
            salary_amount=data.get("salary_amount", 200),
            max_players=data.get("max_players", 4),
        )


# =============================================================================
# Helper function for parsing incoming messages
# =============================================================================

def parse_message(json_str: str) -> Message:
    """
    Parse a JSON string into the appropriate Message subclass.
    
    For now, returns base Message class. The message handler will
    use the type field to determine how to process it.
    """
    return Message.from_json(json_str)
