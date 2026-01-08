"""
Event log widget.

Shows game events and messages in a scrolling log.
"""

from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor, QColor

from shared.enums import MessageType


class EventLog(QWidget):
    """Scrolling log of game events."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("Game Log")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        # Log text area
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 9))
        self._log.setStyleSheet("""
            QTextEdit {
                background-color: #1A252F;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._log)
    
    def add_message(self, text: str, color: str = "#ECF0F1") -> None:
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color: #7F8C8D;">[{timestamp}]</span> '
        html += f'<span style="color: {color};">{text}</span><br>'
        
        self._log.moveCursor(QTextCursor.MoveOperation.End)
        self._log.insertHtml(html)
        self._log.moveCursor(QTextCursor.MoveOperation.End)
    
    def add_system_message(self, text: str) -> None:
        """Add a system message."""
        self.add_message(f"⚙️ {text}", "#3498DB")
    
    def add_error_message(self, text: str) -> None:
        """Add an error message."""
        self.add_message(f"❌ {text}", "#E74C3C")
    
    def add_game_event(self, msg_type: str, data: dict) -> None:
        """Add a game event from server message."""
        text = ""
        color = "#ECF0F1"
        
        if msg_type == MessageType.DICE_ROLLED.value:
            player = data.get("player_name", "Someone")
            d1, d2 = data.get("die1", 0), data.get("die2", 0)
            total = data.get("total", 0)
            is_double = data.get("is_double", False)
            text = f"🎲 {player} rolled {d1} + {d2} = {total}"
            if is_double:
                text += " (DOUBLES!)"
                color = "#F1C40F"
            result = data.get("result_message", "")
            if result:
                text += f" - {result}"
        
        elif msg_type == MessageType.PROPERTY_BOUGHT.value:
            player = data.get("player_name", "Someone")
            prop = data.get("property_name", "a property")
            price = data.get("price", 0)
            text = f"💰 {player} bought {prop} for ${price}"
            color = "#27AE60"
        
        elif msg_type == MessageType.RENT_PAID.value:
            payer = data.get("payer_name", "Someone")
            payee = data.get("payee_name", "someone")
            amount = data.get("amount", 0)
            prop = data.get("property_name", "")
            text = f"💸 {payer} paid ${amount} rent to {payee}"
            if prop:
                text += f" for {prop}"
            color = "#E67E22"
        
        elif msg_type == MessageType.BUILDING_CHANGED.value:
            player = data.get("player_name", "Someone")
            prop = data.get("property_name", "a property")
            action = data.get("action", "")
            if "hotel" in action:
                text = f"🏨 {player} built a hotel on {prop}"
            elif "house" in action and "sold" not in action:
                text = f"🏠 {player} built a house on {prop}"
            else:
                text = f"📉 {player} sold a building on {prop}"
            color = "#9B59B6"
        
        elif msg_type == MessageType.PROPERTY_MORTGAGED.value:
            player = data.get("player_name", "Someone")
            prop = data.get("property_name", "a property")
            is_mortgaged = data.get("is_mortgaged", True)
            if is_mortgaged:
                text = f"🏦 {player} mortgaged {prop}"
            else:
                text = f"💳 {player} unmortgaged {prop}"
            color = "#95A5A6"
        
        elif msg_type == MessageType.JAIL_STATUS.value:
            player = data.get("player_name", "Someone")
            in_jail = data.get("in_jail", False)
            reason = data.get("reason", "")
            if in_jail:
                text = f"🔒 {player} went to jail"
                color = "#E74C3C"
            else:
                reason_text = {
                    "paid_bail": "by paying bail",
                    "used_card": "with a Get Out of Jail card",
                    "rolled_doubles": "by rolling doubles",
                }.get(reason, "")
                text = f"🔓 {player} got out of jail {reason_text}"
                color = "#27AE60"
        
        elif msg_type == MessageType.CARD_DRAWN.value:
            player = data.get("player_name", "Someone")
            card_type = data.get("card_type", "")
            card_text = data.get("card_text", "Drew a card")
            emoji = "🎴" if card_type == "CHANCE" else "📦"
            text = f"{emoji} {player}: {card_text}"
            color = "#F39C12"
        
        elif msg_type == MessageType.TURN_ENDED.value:
            prev = data.get("previous_player_name", "")
            curr = data.get("current_player_name", "")
            turn = data.get("turn_number", 0)
            text = f"➡️ Turn {turn}: {curr}'s turn"
            color = "#3498DB"
        
        elif msg_type == MessageType.PLAYER_BANKRUPT.value:
            player = data.get("player_name", "Someone")
            creditor = data.get("creditor_name")
            text = f"💀 {player} went bankrupt"
            if creditor:
                text += f" (assets to {creditor})"
            color = "#E74C3C"
        
        elif msg_type == MessageType.GAME_WON.value:
            winner = data.get("winner_name", "Someone")
            text = f"🏆 {winner} WINS THE GAME! 🎉"
            color = "#F1C40F"
        
        elif msg_type == MessageType.JOIN_GAME.value:
            player = data.get("player_name", "Someone")
            text = f"👋 {player} joined the game"
            color = "#27AE60"
        
        elif msg_type == MessageType.LEAVE_GAME.value:
            player = data.get("player_name", "Someone")
            text = f"👋 {player} left the game"
            color = "#E74C3C"
        
        elif msg_type == MessageType.GAME_STARTED.value:
            text = "🎮 Game started!"
            color = "#27AE60"
        
        elif msg_type == MessageType.DISCONNECT.value:
            player = data.get("player_name", "Someone")
            text = f"📴 {player} disconnected"
            color = "#E74C3C"
        
        elif msg_type == MessageType.RECONNECT.value:
            player = data.get("player_name", "Someone")
            text = f"📱 {player} reconnected"
            color = "#27AE60"
        
        else:
            # Unknown message type
            text = f"📩 {msg_type}: {data}"
            color = "#7F8C8D"
        
        if text:
            self.add_message(text, color)
    
    def clear(self) -> None:
        """Clear the log."""
        self._log.clear()
