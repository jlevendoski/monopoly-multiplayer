"""
Local game controller.

Wraps the server's game engine for local play without networking.
Provides the same interface as NetworkClient but operates locally.
"""

from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from server.game_engine import Game, Player
from shared.enums import MessageType, GamePhase


class LocalGameController(QObject):
    """
    Controller for local (offline) Monopoly games.
    
    Wraps the server's Game engine and emits Qt signals for UI updates.
    Supports hot-seat multiplayer where players take turns on the same device.
    
    Signals:
        game_state_changed: Game state updated (state_dict)
        game_event: A game event occurred (event_type, event_data)
        error_occurred: An error happened (error_message)
        player_switched: Active player changed (player_id, player_name)
    """
    
    game_state_changed = pyqtSignal(dict)
    game_event = pyqtSignal(str, dict)
    error_occurred = pyqtSignal(str)
    player_switched = pyqtSignal(str, str)  # player_id, player_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._game: Optional[Game] = None
        self._active_player_id: Optional[str] = None
    
    @property
    def game(self) -> Optional[Game]:
        """The current game instance."""
        return self._game
    
    @property
    def active_player_id(self) -> Optional[str]:
        """The currently active player (whose turn it is to interact)."""
        return self._active_player_id
    
    @property
    def is_game_active(self) -> bool:
        """Whether a game is in progress."""
        return self._game is not None and self._game.phase not in (
            GamePhase.WAITING, GamePhase.GAME_OVER
        )
    
    def get_state(self, player_id: Optional[str] = None) -> dict:
        """Get the current game state."""
        if not self._game:
            return {}
        
        pid = player_id or self._active_player_id
        state = self._game.get_state_for_player(pid or "")
        
        # Add local-specific info
        state["is_local_game"] = True
        state["active_player_id"] = self._active_player_id
        
        return state
    
    def _emit_state(self) -> None:
        """Emit the current game state."""
        if self._game:
            self.game_state_changed.emit(self.get_state())
    
    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit a game event."""
        self.game_event.emit(event_type, data)
    
    # =========================================================================
    # Game Setup
    # =========================================================================
    
    def create_game(self, game_name: str = "Local Game") -> None:
        """Create a new local game."""
        self._game = Game(name=game_name)
        self._active_player_id = None
        self._emit_state()
    
    def add_player(self, name: str) -> Optional[str]:
        """
        Add a player to the game.
        
        Returns:
            Player ID if successful, None otherwise.
        """
        if not self._game:
            self.error_occurred.emit("No game created")
            return None
        
        success, msg, player = self._game.add_player(name)
        
        if not success:
            self.error_occurred.emit(msg)
            return None
        
        self._emit_event(MessageType.JOIN_GAME.value, {
            "player_id": player.id,
            "player_name": player.name,
            "game_id": self._game.id,
        })
        
        self._emit_state()
        return player.id
    
    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the game."""
        if not self._game:
            return False
        
        player = self._game.players.get(player_id)
        if not player:
            return False
        
        player_name = player.name
        success, msg = self._game.remove_player(player_id)
        
        if success:
            self._emit_event(MessageType.LEAVE_GAME.value, {
                "player_id": player_id,
                "player_name": player_name,
            })
            self._emit_state()
        else:
            self.error_occurred.emit(msg)
        
        return success
    
    def start_game(self) -> bool:
        """Start the game."""
        if not self._game:
            self.error_occurred.emit("No game created")
            return False
        
        success, msg = self._game.start_game()
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        # Set active player to first player
        if self._game.current_player:
            self._active_player_id = self._game.current_player.id
            self.player_switched.emit(
                self._active_player_id,
                self._game.current_player.name
            )
        
        self._emit_event(MessageType.GAME_STARTED.value, {
            "game_id": self._game.id,
            "game_name": self._game.name,
        })
        
        self._emit_state()
        return True
    
    # =========================================================================
    # Game Actions
    # =========================================================================
    
    def roll_dice(self) -> bool:
        """Roll the dice for the current player."""
        if not self._game or not self._active_player_id:
            self.error_occurred.emit("No active game or player")
            return False
        
        success, msg, result = self._game.roll_dice(self._active_player_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.DICE_ROLLED.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "die1": result.die1,
            "die2": result.die2,
            "total": result.total,
            "is_double": result.is_double,
            "result_message": msg,
        })
        
        # Check for jail status change
        if player and "jail" in msg.lower():
            self._emit_event(MessageType.JAIL_STATUS.value, {
                "player_id": self._active_player_id,
                "player_name": player.name,
                "in_jail": player.state.value == "IN_JAIL",
                "reason": "rolled_doubles" if result.is_double else "sent_to_jail",
            })
        
        self._emit_state()
        return True
    
    def buy_property(self) -> bool:
        """Buy the property at current position."""
        if not self._game or not self._active_player_id:
            return False
        
        player = self._game.players.get(self._active_player_id)
        if not player:
            return False
        
        position = player.position
        prop = self._game.board.get_property(position)
        
        success, msg = self._game.buy_property(self._active_player_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        self._emit_event(MessageType.PROPERTY_BOUGHT.value, {
            "player_id": self._active_player_id,
            "player_name": player.name,
            "property_name": prop.name if prop else "Unknown",
            "position": position,
            "price": prop.cost if prop else 0,
        })
        
        self._emit_state()
        return True
    
    def decline_property(self) -> bool:
        """Decline to buy the current property."""
        if not self._game or not self._active_player_id:
            return False
        
        success, msg = self._game.decline_property(self._active_player_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        self._emit_state()
        return True
    
    def end_turn(self) -> bool:
        """End the current player's turn."""
        if not self._game or not self._active_player_id:
            return False
        
        prev_player = self._game.current_player
        prev_name = prev_player.name if prev_player else "Unknown"
        prev_id = prev_player.id if prev_player else ""
        
        success, msg = self._game.end_turn(self._active_player_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        # Check for game over
        if self._game.phase == GamePhase.GAME_OVER:
            winner = self._game.players.get(self._game.winner_id) if self._game.winner_id else None
            self._emit_event(MessageType.GAME_WON.value, {
                "winner_id": self._game.winner_id or "",
                "winner_name": winner.name if winner else "Unknown",
            })
            self._active_player_id = None
        else:
            # Switch to next player
            current = self._game.current_player
            if current:
                self._active_player_id = current.id
                self.player_switched.emit(current.id, current.name)
                
                self._emit_event(MessageType.TURN_ENDED.value, {
                    "previous_player_id": prev_id,
                    "previous_player_name": prev_name,
                    "current_player_id": current.id,
                    "current_player_name": current.name,
                    "turn_number": self._game.turn_number,
                })
        
        self._emit_state()
        return True
    
    def build_house(self, position: int) -> bool:
        """Build a house on a property."""
        if not self._game or not self._active_player_id:
            return False
        
        prop = self._game.board.get_property(position)
        success, msg = self._game.build_house(self._active_player_id, position)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.BUILDING_CHANGED.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "property_name": prop.name if prop else "Unknown",
            "position": position,
            "action": "built_house",
            "houses": prop.houses if prop else 0,
            "has_hotel": prop.has_hotel if prop else False,
        })
        
        self._emit_state()
        return True
    
    def build_hotel(self, position: int) -> bool:
        """Build a hotel on a property."""
        if not self._game or not self._active_player_id:
            return False
        
        prop = self._game.board.get_property(position)
        success, msg = self._game.build_hotel(self._active_player_id, position)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.BUILDING_CHANGED.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "property_name": prop.name if prop else "Unknown",
            "position": position,
            "action": "built_hotel",
            "houses": 0,
            "has_hotel": True,
        })
        
        self._emit_state()
        return True
    
    def sell_building(self, position: int) -> bool:
        """Sell a building from a property."""
        if not self._game or not self._active_player_id:
            return False
        
        prop = self._game.board.get_property(position)
        had_hotel = prop.has_hotel if prop else False
        
        success, msg = self._game.sell_building(self._active_player_id, position)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.BUILDING_CHANGED.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "property_name": prop.name if prop else "Unknown",
            "position": position,
            "action": "sold_hotel" if had_hotel else "sold_house",
            "houses": prop.houses if prop else 0,
            "has_hotel": prop.has_hotel if prop else False,
        })
        
        self._emit_state()
        return True
    
    def mortgage_property(self, position: int) -> bool:
        """Mortgage a property."""
        if not self._game or not self._active_player_id:
            return False
        
        prop = self._game.board.get_property(position)
        success, msg = self._game.mortgage_property(self._active_player_id, position)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.PROPERTY_MORTGAGED.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "property_name": prop.name if prop else "Unknown",
            "position": position,
            "is_mortgaged": True,
            "amount": prop.mortgage_value if prop else 0,
        })
        
        self._emit_state()
        return True
    
    def unmortgage_property(self, position: int) -> bool:
        """Unmortgage a property."""
        if not self._game or not self._active_player_id:
            return False
        
        prop = self._game.board.get_property(position)
        success, msg = self._game.unmortgage_property(self._active_player_id, position)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.PROPERTY_MORTGAGED.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "property_name": prop.name if prop else "Unknown",
            "position": position,
            "is_mortgaged": False,
            "amount": prop.unmortgage_cost if prop else 0,
        })
        
        self._emit_state()
        return True
    
    def pay_bail(self) -> bool:
        """Pay bail to get out of jail."""
        if not self._game or not self._active_player_id:
            return False
        
        success, msg = self._game.pay_bail(self._active_player_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.JAIL_STATUS.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "in_jail": False,
            "reason": "paid_bail",
        })
        
        self._emit_state()
        return True
    
    def use_jail_card(self) -> bool:
        """Use a Get Out of Jail Free card."""
        if not self._game or not self._active_player_id:
            return False
        
        success, msg = self._game.use_jail_card(self._active_player_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        player = self._game.players.get(self._active_player_id)
        
        self._emit_event(MessageType.JAIL_STATUS.value, {
            "player_id": self._active_player_id,
            "player_name": player.name if player else "Unknown",
            "in_jail": False,
            "reason": "used_card",
        })
        
        self._emit_state()
        return True
    
    def declare_bankruptcy(self, creditor_id: Optional[str] = None) -> bool:
        """Declare bankruptcy."""
        if not self._game or not self._active_player_id:
            return False
        
        player = self._game.players.get(self._active_player_id)
        player_name = player.name if player else "Unknown"
        
        creditor = self._game.players.get(creditor_id) if creditor_id else None
        creditor_name = creditor.name if creditor else None
        
        success, msg = self._game.declare_bankruptcy(self._active_player_id, creditor_id)
        
        if not success:
            self.error_occurred.emit(msg)
            return False
        
        self._emit_event(MessageType.PLAYER_BANKRUPT.value, {
            "player_id": self._active_player_id,
            "player_name": player_name,
            "creditor_id": creditor_id,
            "creditor_name": creditor_name,
        })
        
        # Check for game over
        if self._game.phase == GamePhase.GAME_OVER:
            winner = self._game.players.get(self._game.winner_id) if self._game.winner_id else None
            self._emit_event(MessageType.GAME_WON.value, {
                "winner_id": self._game.winner_id or "",
                "winner_name": winner.name if winner else "Unknown",
            })
            self._active_player_id = None
        else:
            # Switch to next player if current went bankrupt
            current = self._game.current_player
            if current:
                self._active_player_id = current.id
                self.player_switched.emit(current.id, current.name)
        
        self._emit_state()
        return True
