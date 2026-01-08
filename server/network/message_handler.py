"""
Message handler for routing client messages to game actions.

Parses incoming messages, validates them, executes the appropriate
game actions, and formats responses and broadcasts.
"""

import logging
from dataclasses import dataclass
from typing import Any

from server.game_engine import Game
from server.network.game_manager import GameManager, ManagedGame
from server.network.connection_manager import ConnectionManager
from shared.protocol import (
    Message,
    ErrorMessage,
    GameListResponse,
    GameStateMessage,
    GameStartedMessage,
    DiceRolledMessage,
    PropertyBoughtMessage,
    BuildingChangedMessage,
    PropertyMortgagedMessage,
    TurnEndedMessage,
    JailStatusMessage,
    CardDrawnMessage,
    PlayerBankruptMessage,
    GameWonMessage,
    PlayerJoinedMessage,
    PlayerLeftMessage,
    PlayerKickedMessage,
    HostTransferredMessage,
    GameSettings,
    parse_message,
)
from shared.enums import MessageType, GamePhase


logger = logging.getLogger(__name__)


@dataclass
class HandleResult:
    """Result of handling a message."""
    # Response to send back to the requesting player (None if no response needed)
    response: Message | None = None
    # Messages to broadcast to all players in the game
    broadcasts: list[Message] | None = None
    # Whether to broadcast the full game state after this action
    broadcast_state: bool = False
    # Whether to trigger auto-save after this action
    should_save: bool = False


class MessageHandler:
    """
    Routes incoming messages to appropriate game actions.
    
    Each handler method returns a HandleResult containing:
    - A response to send to the requesting player
    - Broadcasts to send to all players in the game
    - Flags for state broadcast and auto-save
    """
    
    def __init__(self, game_manager: GameManager, connection_manager: ConnectionManager):
        self._games = game_manager
        self._connections = connection_manager
    
    async def handle_message(
        self,
        player_id: str,
        message: Message | str | dict
    ) -> HandleResult:
        """
        Handle an incoming message from a player.
        
        Args:
            player_id: ID of the player sending the message
            message: The message (Message object, JSON string, or dict)
            
        Returns:
            HandleResult with response and broadcasts
        """
        # Parse message if needed
        if isinstance(message, str):
            try:
                message = parse_message(message)
            except Exception as e:
                logger.error(f"Failed to parse message: {e}")
                return HandleResult(
                    response=ErrorMessage.create(f"Invalid message format: {e}", "PARSE_ERROR")
                )
        elif isinstance(message, dict):
            try:
                message = Message.from_dict(message)
            except Exception as e:
                logger.error(f"Failed to parse message dict: {e}")
                return HandleResult(
                    response=ErrorMessage.create(f"Invalid message format: {e}", "PARSE_ERROR")
                )
        
        # Route to appropriate handler
        handler = self._get_handler(message.type)
        if not handler:
            return HandleResult(
                response=ErrorMessage.create(
                    f"Unknown message type: {message.type.value}",
                    "UNKNOWN_MESSAGE_TYPE",
                    message.request_id
                )
            )
        
        try:
            result = await handler(player_id, message)
            
            # Preserve request_id in response
            if result.response and message.request_id:
                result.response.request_id = message.request_id
            
            return result
            
        except Exception as e:
            logger.exception(f"Error handling message {message.type}: {e}")
            return HandleResult(
                response=ErrorMessage.create(
                    f"Internal error: {e}",
                    "INTERNAL_ERROR",
                    message.request_id
                )
            )
    
    def _get_handler(self, message_type: MessageType):
        """Get the handler method for a message type."""
        handlers = {
            # Lobby
            MessageType.LIST_GAMES: self._handle_list_games,
            MessageType.CREATE_GAME: self._handle_create_game,
            MessageType.JOIN_GAME: self._handle_join_game,
            MessageType.LEAVE_GAME: self._handle_leave_game,
            MessageType.START_GAME: self._handle_start_game,
            
            # Host privileges
            MessageType.KICK_PLAYER: self._handle_kick_player,
            MessageType.TRANSFER_HOST: self._handle_transfer_host,
            
            # Game actions
            MessageType.ROLL_DICE: self._handle_roll_dice,
            MessageType.BUY_PROPERTY: self._handle_buy_property,
            MessageType.DECLINE_PROPERTY: self._handle_decline_property,
            MessageType.BUILD_HOUSE: self._handle_build_house,
            MessageType.BUILD_HOTEL: self._handle_build_hotel,
            MessageType.SELL_BUILDING: self._handle_sell_building,
            MessageType.MORTGAGE_PROPERTY: self._handle_mortgage_property,
            MessageType.UNMORTGAGE_PROPERTY: self._handle_unmortgage_property,
            MessageType.PAY_BAIL: self._handle_pay_bail,
            MessageType.USE_JAIL_CARD: self._handle_use_jail_card,
            MessageType.END_TURN: self._handle_end_turn,
            MessageType.PLAYER_BANKRUPT: self._handle_declare_bankruptcy,
            
            # State query
            MessageType.GAME_STATE: self._handle_get_state,
        }
        return handlers.get(message_type)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_player_game(self, player_id: str) -> tuple[ManagedGame | None, str | None]:
        """Get the game a player is in, or error message."""
        managed = self._games.get_game_for_player(player_id)
        if not managed:
            return None, "You are not in a game"
        return managed, None
    
    def _create_state_message(self, game: Game, player_id: str) -> GameStateMessage:
        """Create a game state message for a player."""
        return GameStateMessage.create(game.get_state_for_player(player_id))
    
    def _get_player_name(self, game: Game, player_id: str) -> str:
        """Get a player's name from the game."""
        player = game.players.get(player_id)
        return player.name if player else "Unknown"
    
    # =========================================================================
    # Lobby Handlers
    # =========================================================================
    
    async def _handle_list_games(self, player_id: str, message: Message) -> HandleResult:
        """Handle LIST_GAMES request."""
        status = message.data.get("status")
        games = self._games.list_joinable_games() if not status else self._games.list_games(status)
        
        return HandleResult(
            response=GameListResponse.create(games)
        )
    
    async def _handle_create_game(self, player_id: str, message: Message) -> HandleResult:
        """Handle CREATE_GAME request."""
        game_name = message.data.get("game_name", "Unnamed Game")
        player_name = message.data.get("player_name", "Player")
        settings_data = message.data.get("settings", {})
        settings = GameSettings.from_dict(settings_data)
        
        success, msg, managed = self._games.create_game(
            name=game_name,
            host_player_id=player_id,
            host_player_name=player_name,
            settings=settings
        )
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "CREATE_GAME_FAILED")
            )
        
        # Associate connection with game
        await self._connections.join_game(player_id, managed.game_id, is_host=True)
        
        return HandleResult(
            response=self._create_state_message(managed.game, player_id)
        )
    
    async def _handle_join_game(self, player_id: str, message: Message) -> HandleResult:
        """Handle JOIN_GAME request."""
        game_id = message.data.get("game_id")
        player_name = message.data.get("player_name", "Player")
        as_spectator = message.data.get("as_spectator", False)
        
        if not game_id:
            return HandleResult(
                response=ErrorMessage.create("game_id is required", "MISSING_GAME_ID")
            )
        
        success, msg, player = self._games.join_game(
            game_id=game_id,
            player_id=player_id,
            player_name=player_name,
            as_spectator=as_spectator
        )
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "JOIN_GAME_FAILED")
            )
        
        # Associate connection with game
        await self._connections.join_game(
            player_id, 
            game_id, 
            is_host=False,
            is_spectator=as_spectator
        )
        
        managed = self._games.get_game(game_id)
        
        # Broadcast to other players that someone joined
        broadcasts = [
            PlayerJoinedMessage.create(
                player_id=player_id,
                player_name=player_name,
                game_id=game_id
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(managed.game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True  # Everyone gets updated state
        )
    
    async def _handle_leave_game(self, player_id: str, message: Message) -> HandleResult:
        """Handle LEAVE_GAME request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        player_name = self._get_player_name(managed.game, player_id)
        game_id = managed.game_id
        
        success, msg, _ = self._games.leave_game(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "LEAVE_GAME_FAILED")
            )
        
        # Update connection
        await self._connections.leave_game(player_id)
        
        # Broadcast to remaining players
        broadcasts = [
            PlayerLeftMessage.create(player_id=player_id, player_name=player_name)
        ]
        
        return HandleResult(
            response=Message(type=MessageType.LEAVE_GAME, data={"success": True}),
            broadcasts=broadcasts,
            broadcast_state=True,
            should_save=managed.is_started  # Save if game was in progress
        )
    
    async def _handle_start_game(self, player_id: str, message: Message) -> HandleResult:
        """Handle START_GAME request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        success, msg = self._games.start_game(managed.game_id, player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "START_GAME_FAILED")
            )
        
        # Broadcast game started to all players
        broadcasts = [
            GameStartedMessage.create(managed.game.to_dict())
        ]
        
        return HandleResult(
            response=self._create_state_message(managed.game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True,
            should_save=True
        )
    
    # =========================================================================
    # Host Privilege Handlers
    # =========================================================================
    
    async def _handle_kick_player(self, player_id: str, message: Message) -> HandleResult:
        """Handle KICK_PLAYER request (host only)."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        target_id = message.data.get("player_id")
        if not target_id:
            return HandleResult(
                response=ErrorMessage.create("player_id is required", "MISSING_PLAYER_ID")
            )
        
        target_name = self._get_player_name(managed.game, target_id)
        
        success, msg = self._games.remove_player(managed.game_id, target_id, player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "KICK_PLAYER_FAILED")
            )
        
        # Update connection manager
        await self._connections.leave_game(target_id)
        
        # Notify kicked player if connected
        await self._connections.send_to_player(
            target_id,
            ErrorMessage.create("You have been kicked from the game", "KICKED")
        )
        
        broadcasts = [
            PlayerKickedMessage.create(
                player_id=target_id,
                player_name=target_name,
                kicked_by=self._get_player_name(managed.game, player_id)
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(managed.game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_transfer_host(self, player_id: str, message: Message) -> HandleResult:
        """Handle TRANSFER_HOST request (host only)."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        if managed.host_player_id != player_id:
            return HandleResult(
                response=ErrorMessage.create("Only the host can transfer host privileges", "NOT_HOST")
            )
        
        new_host_id = message.data.get("player_id")
        if not new_host_id:
            return HandleResult(
                response=ErrorMessage.create("player_id is required", "MISSING_PLAYER_ID")
            )
        
        if new_host_id not in managed.game.players:
            return HandleResult(
                response=ErrorMessage.create("Player not in game", "PLAYER_NOT_FOUND")
            )
        
        old_host_id = managed.host_player_id
        new_host_name = self._get_player_name(managed.game, new_host_id)
        
        # Update game manager
        managed.host_player_id = new_host_id
        
        # Update connection manager
        await self._connections.transfer_host(managed.game_id, new_host_id)
        
        broadcasts = [
            HostTransferredMessage.create(
                new_host_id=new_host_id,
                new_host_name=new_host_name,
                old_host_id=old_host_id
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(managed.game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    # =========================================================================
    # Game Action Handlers
    # =========================================================================
    
    async def _handle_roll_dice(self, player_id: str, message: Message) -> HandleResult:
        """Handle ROLL_DICE request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        success, msg, dice_result = game.roll_dice(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "ROLL_DICE_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            DiceRolledMessage.create(
                player_id=player_id,
                player_name=player_name,
                die1=dice_result.die1,
                die2=dice_result.die2,
                total=dice_result.total,
                is_double=dice_result.is_double,
                result_message=msg
            )
        ]
        
        # Check for jail status change
        player = game.players.get(player_id)
        if player and msg and "jail" in msg.lower():
            broadcasts.append(
                JailStatusMessage.create(
                    player_id=player_id,
                    player_name=player_name,
                    in_jail=player.state.value == "IN_JAIL",
                    reason="rolled_doubles" if dice_result.is_double else "sent_to_jail"
                )
            )
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_buy_property(self, player_id: str, message: Message) -> HandleResult:
        """Handle BUY_PROPERTY request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        player = game.players.get(player_id)
        position = player.position if player else 0
        prop = game.board.get_property(position)
        
        success, msg = game.buy_property(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "BUY_PROPERTY_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            PropertyBoughtMessage.create(
                player_id=player_id,
                player_name=player_name,
                property_name=prop.name if prop else "Unknown",
                position=position,
                price=prop.cost if prop else 0
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_decline_property(self, player_id: str, message: Message) -> HandleResult:
        """Handle DECLINE_PROPERTY request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        success, msg = game.decline_property(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "DECLINE_PROPERTY_FAILED")
            )
        
        # House rules: no auction, property just stays unowned
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcast_state=True
        )
    
    async def _handle_build_house(self, player_id: str, message: Message) -> HandleResult:
        """Handle BUILD_HOUSE request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        position = message.data.get("position")
        if position is None:
            return HandleResult(
                response=ErrorMessage.create("position is required", "MISSING_POSITION")
            )
        
        game = managed.game
        prop = game.board.get_property(position)
        
        success, msg = game.build_house(player_id, position)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "BUILD_HOUSE_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            BuildingChangedMessage.create(
                player_id=player_id,
                player_name=player_name,
                property_name=prop.name if prop else "Unknown",
                position=position,
                action="built_house",
                houses=prop.houses if prop else 0,
                has_hotel=prop.has_hotel if prop else False
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_build_hotel(self, player_id: str, message: Message) -> HandleResult:
        """Handle BUILD_HOTEL request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        position = message.data.get("position")
        if position is None:
            return HandleResult(
                response=ErrorMessage.create("position is required", "MISSING_POSITION")
            )
        
        game = managed.game
        prop = game.board.get_property(position)
        
        success, msg = game.build_hotel(player_id, position)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "BUILD_HOTEL_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            BuildingChangedMessage.create(
                player_id=player_id,
                player_name=player_name,
                property_name=prop.name if prop else "Unknown",
                position=position,
                action="built_hotel",
                houses=0,
                has_hotel=True
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_sell_building(self, player_id: str, message: Message) -> HandleResult:
        """Handle SELL_BUILDING request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        position = message.data.get("position")
        if position is None:
            return HandleResult(
                response=ErrorMessage.create("position is required", "MISSING_POSITION")
            )
        
        game = managed.game
        prop = game.board.get_property(position)
        had_hotel = prop.has_hotel if prop else False
        
        success, msg = game.sell_building(player_id, position)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "SELL_BUILDING_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            BuildingChangedMessage.create(
                player_id=player_id,
                player_name=player_name,
                property_name=prop.name if prop else "Unknown",
                position=position,
                action="sold_hotel" if had_hotel else "sold_house",
                houses=prop.houses if prop else 0,
                has_hotel=prop.has_hotel if prop else False
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_mortgage_property(self, player_id: str, message: Message) -> HandleResult:
        """Handle MORTGAGE_PROPERTY request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        position = message.data.get("position")
        if position is None:
            return HandleResult(
                response=ErrorMessage.create("position is required", "MISSING_POSITION")
            )
        
        game = managed.game
        prop = game.board.get_property(position)
        
        success, msg = game.mortgage_property(player_id, position)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "MORTGAGE_PROPERTY_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            PropertyMortgagedMessage.create(
                player_id=player_id,
                player_name=player_name,
                property_name=prop.name if prop else "Unknown",
                position=position,
                is_mortgaged=True,
                amount=prop.mortgage_value if prop else 0
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_unmortgage_property(self, player_id: str, message: Message) -> HandleResult:
        """Handle UNMORTGAGE_PROPERTY request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        position = message.data.get("position")
        if position is None:
            return HandleResult(
                response=ErrorMessage.create("position is required", "MISSING_POSITION")
            )
        
        game = managed.game
        prop = game.board.get_property(position)
        
        success, msg = game.unmortgage_property(player_id, position)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "UNMORTGAGE_PROPERTY_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            PropertyMortgagedMessage.create(
                player_id=player_id,
                player_name=player_name,
                property_name=prop.name if prop else "Unknown",
                position=position,
                is_mortgaged=False,
                amount=prop.unmortgage_cost if prop else 0
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_pay_bail(self, player_id: str, message: Message) -> HandleResult:
        """Handle PAY_BAIL request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        success, msg = game.pay_bail(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "PAY_BAIL_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            JailStatusMessage.create(
                player_id=player_id,
                player_name=player_name,
                in_jail=False,
                reason="paid_bail"
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_use_jail_card(self, player_id: str, message: Message) -> HandleResult:
        """Handle USE_JAIL_CARD request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        success, msg = game.use_jail_card(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "USE_JAIL_CARD_FAILED")
            )
        
        player_name = self._get_player_name(game, player_id)
        
        broadcasts = [
            JailStatusMessage.create(
                player_id=player_id,
                player_name=player_name,
                in_jail=False,
                reason="used_card"
            )
        ]
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True
        )
    
    async def _handle_end_turn(self, player_id: str, message: Message) -> HandleResult:
        """Handle END_TURN request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        previous_player = game.current_player
        previous_id = previous_player.id if previous_player else None
        previous_name = previous_player.name if previous_player else "Unknown"
        
        success, msg = game.end_turn(player_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "END_TURN_FAILED")
            )
        
        broadcasts = []
        
        # Check if game is over
        if game.phase == GamePhase.GAME_OVER:
            winner = game.players.get(game.winner_id) if game.winner_id else None
            broadcasts.append(
                GameWonMessage.create(
                    winner_id=game.winner_id or "",
                    winner_name=winner.name if winner else "Unknown"
                )
            )
        else:
            current_player = game.current_player
            broadcasts.append(
                TurnEndedMessage.create(
                    previous_player_id=previous_id or "",
                    previous_player_name=previous_name,
                    current_player_id=current_player.id if current_player else "",
                    current_player_name=current_player.name if current_player else "Unknown",
                    turn_number=game.turn_number
                )
            )
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True,
            should_save=True  # Auto-save after each turn
        )
    
    async def _handle_declare_bankruptcy(self, player_id: str, message: Message) -> HandleResult:
        """Handle PLAYER_BANKRUPT (declare bankruptcy) request."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        game = managed.game
        player_name = self._get_player_name(game, player_id)
        creditor_id = message.data.get("creditor_id")
        creditor_name = self._get_player_name(game, creditor_id) if creditor_id else None
        
        success, msg = game.declare_bankruptcy(player_id, creditor_id)
        
        if not success:
            return HandleResult(
                response=ErrorMessage.create(msg, "BANKRUPTCY_FAILED")
            )
        
        broadcasts = [
            PlayerBankruptMessage.create(
                player_id=player_id,
                player_name=player_name,
                creditor_id=creditor_id,
                creditor_name=creditor_name
            )
        ]
        
        # Check if game is over
        if game.phase == GamePhase.GAME_OVER:
            winner = game.players.get(game.winner_id) if game.winner_id else None
            broadcasts.append(
                GameWonMessage.create(
                    winner_id=game.winner_id or "",
                    winner_name=winner.name if winner else "Unknown"
                )
            )
        
        return HandleResult(
            response=self._create_state_message(game, player_id),
            broadcasts=broadcasts,
            broadcast_state=True,
            should_save=True
        )
    
    # =========================================================================
    # State Query Handler
    # =========================================================================
    
    async def _handle_get_state(self, player_id: str, message: Message) -> HandleResult:
        """Handle GAME_STATE request (get current state)."""
        managed, error = self._get_player_game(player_id)
        if error:
            return HandleResult(
                response=ErrorMessage.create(error, "NOT_IN_GAME")
            )
        
        return HandleResult(
            response=self._create_state_message(managed.game, player_id)
        )
