"""
Board visualization widget.

Draws the Monopoly board with properties, players, and buildings.
Uses placeholder graphics - designed to be easily replaced with images.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics

from shared.constants import BOARD_SIZE, BOARD_SPACES
from client.gui.styles import (
    PROPERTY_COLORS, PLAYER_COLORS, SPACE_COLORS,
    BACKGROUND_COLOR, BOARD_EDGE_COLOR, MORTGAGED_OVERLAY
)


class BoardWidget(QWidget):
    """
    Widget that draws the Monopoly board.
    
    The board is drawn as a square with spaces around the edges.
    Players are shown as colored circles on their current positions.
    """
    
    # Signal emitted when a space is clicked
    space_clicked = pyqtSignal(int)  # position
    
    # Board layout: positions 0-9 bottom, 10-19 left, 20-29 top, 30-39 right
    SPACES_PER_SIDE = 11  # Including corners
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._game_state: Optional[dict] = None
        self._player_id: Optional[str] = None
        self._hovered_space: Optional[int] = None
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Minimum size
        self.setMinimumSize(500, 500)
    
    def set_game_state(self, state: dict, player_id: str) -> None:
        """Update the game state and redraw."""
        self._game_state = state
        self._player_id = player_id
        self.update()
    
    def clear(self) -> None:
        """Clear the game state."""
        self._game_state = None
        self.update()
    
    def _get_space_rect(self, position: int) -> QRect:
        """Get the rectangle for a board position."""
        size = min(self.width(), self.height())
        margin = 10
        board_size = size - 2 * margin
        
        # Corner spaces are square, edge spaces are rectangular
        corner_size = board_size // 8
        edge_width = (board_size - 2 * corner_size) // 9
        edge_height = corner_size
        
        if position == 0:  # GO - bottom right corner
            return QRect(
                margin + board_size - corner_size,
                margin + board_size - corner_size,
                corner_size, corner_size
            )
        elif position == 10:  # Jail - bottom left corner
            return QRect(margin, margin + board_size - corner_size, corner_size, corner_size)
        elif position == 20:  # Free Parking - top left corner
            return QRect(margin, margin, corner_size, corner_size)
        elif position == 30:  # Go To Jail - top right corner
            return QRect(margin + board_size - corner_size, margin, corner_size, corner_size)
        elif 1 <= position <= 9:  # Bottom edge (right to left)
            x = margin + board_size - corner_size - (position) * edge_width
            y = margin + board_size - edge_height
            return QRect(x, y, edge_width, edge_height)
        elif 11 <= position <= 19:  # Left edge (bottom to top)
            x = margin
            y = margin + board_size - corner_size - (position - 10) * edge_width
            return QRect(x, y, edge_height, edge_width)
        elif 21 <= position <= 29:  # Top edge (left to right)
            x = margin + corner_size + (position - 21) * edge_width
            y = margin
            return QRect(x, y, edge_width, edge_height)
        elif 31 <= position <= 39:  # Right edge (top to bottom)
            x = margin + board_size - edge_height
            y = margin + corner_size + (position - 31) * edge_width
            return QRect(x, y, edge_height, edge_width)
        
        return QRect()
    
    def _position_from_point(self, point: QPoint) -> Optional[int]:
        """Get the board position from a point."""
        for pos in range(BOARD_SIZE):
            if self._get_space_rect(pos).contains(point):
                return pos
        return None
    
    def paintEvent(self, event) -> None:
        """Draw the board."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        size = min(self.width(), self.height())
        margin = 10
        board_size = size - 2 * margin
        
        # Board background (center area)
        painter.fillRect(
            margin, margin, board_size, board_size,
            BACKGROUND_COLOR
        )
        
        # Draw "MONOPOLY" in center
        painter.setPen(QPen(BOARD_EDGE_COLOR))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            QRect(margin, margin, board_size, board_size),
            Qt.AlignmentFlag.AlignCenter,
            "MONOPOLY"
        )
        
        # Draw all spaces
        for pos in range(BOARD_SIZE):
            self._draw_space(painter, pos)
        
        # Draw players
        if self._game_state:
            self._draw_players(painter)
    
    def _draw_space(self, painter: QPainter, position: int) -> None:
        """Draw a single board space."""
        rect = self._get_space_rect(position)
        space_data = BOARD_SPACES.get(position, {})
        space_type = space_data.get("type", "")
        space_name = space_data.get("name", f"Space {position}")
        space_group = space_data.get("group")
        
        # Get property data if we have game state
        prop_data = None
        if self._game_state:
            prop_data = self._game_state.get("board", {}).get(str(position))
        
        # Background color
        if space_group and space_group in PROPERTY_COLORS:
            bg_color = PROPERTY_COLORS[space_group]
        elif space_type in SPACE_COLORS:
            bg_color = SPACE_COLORS[space_type]
        else:
            bg_color = QColor(255, 255, 255)
        
        # Draw background
        painter.fillRect(rect, bg_color)
        
        # Draw border
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawRect(rect)
        
        # Draw color bar for properties
        if space_group and space_group in PROPERTY_COLORS and space_type == "PROPERTY":
            bar_height = rect.height() // 5
            is_vertical = position in range(11, 20) or position in range(31, 40)
            
            if is_vertical:
                if position in range(11, 20):  # Left side
                    bar_rect = QRect(rect.right() - bar_height, rect.top(), bar_height, rect.height())
                else:  # Right side
                    bar_rect = QRect(rect.left(), rect.top(), bar_height, rect.height())
            else:
                if position in range(1, 10):  # Bottom
                    bar_rect = QRect(rect.left(), rect.top(), rect.width(), bar_height)
                else:  # Top
                    bar_rect = QRect(rect.left(), rect.bottom() - bar_height, rect.width(), bar_height)
            
            painter.fillRect(bar_rect, PROPERTY_COLORS[space_group])
            painter.drawRect(bar_rect)
        
        # Draw mortgaged overlay
        if prop_data and prop_data.get("is_mortgaged"):
            painter.fillRect(rect, MORTGAGED_OVERLAY)
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())
        
        # Draw buildings
        if prop_data:
            houses = prop_data.get("houses", 0)
            has_hotel = prop_data.get("has_hotel", False)
            
            if has_hotel or houses > 0:
                self._draw_buildings(painter, rect, houses, has_hotel, position)
        
        # Draw owner indicator
        if prop_data and prop_data.get("owner_id"):
            owner_id = prop_data["owner_id"]
            if self._game_state:
                players = self._game_state.get("players", [])
                for i, p in enumerate(players):
                    if p.get("id") == owner_id:
                        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
                        painter.setBrush(QBrush(color))
                        painter.setPen(QPen(Qt.GlobalColor.black, 1))
                        # Small circle in corner
                        indicator_size = 8
                        painter.drawEllipse(
                            rect.left() + 2, 
                            rect.bottom() - indicator_size - 2,
                            indicator_size, indicator_size
                        )
                        break
        
        # Draw space name (abbreviated)
        painter.setPen(QPen(Qt.GlobalColor.black))
        font = QFont("Arial", 6)
        painter.setFont(font)
        
        # Abbreviate name to fit
        fm = QFontMetrics(font)
        short_name = space_name
        if len(short_name) > 12:
            short_name = short_name[:10] + ".."
        
        # Rotate text for side spaces
        painter.save()
        if position in range(11, 20):  # Left side - rotate 90°
            painter.translate(rect.center())
            painter.rotate(90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2, rect.height(), rect.width()),
                Qt.AlignmentFlag.AlignCenter,
                short_name
            )
        elif position in range(31, 40):  # Right side - rotate -90°
            painter.translate(rect.center())
            painter.rotate(-90)
            painter.drawText(
                QRect(-rect.height()//2, -rect.width()//2, rect.height(), rect.width()),
                Qt.AlignmentFlag.AlignCenter,
                short_name
            )
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, short_name)
        painter.restore()
        
        # Highlight hovered space
        if self._hovered_space == position:
            painter.fillRect(rect, QColor(255, 255, 0, 50))
    
    def _draw_buildings(
        self, 
        painter: QPainter, 
        rect: QRect, 
        houses: int, 
        has_hotel: bool,
        position: int
    ) -> None:
        """Draw houses or hotel on a property."""
        building_size = 6
        spacing = 2
        
        # Determine building placement based on position
        is_vertical = position in range(11, 20) or position in range(31, 40)
        
        if has_hotel:
            # Draw red hotel
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            if is_vertical:
                x = rect.center().x() - building_size // 2
                y = rect.top() + 4
                painter.drawRect(x, y, building_size, building_size + 2)
            else:
                x = rect.left() + 4
                y = rect.center().y() - building_size // 2
                painter.drawRect(x, y, building_size + 2, building_size)
        else:
            # Draw green houses
            painter.setBrush(QBrush(QColor(0, 128, 0)))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            
            for i in range(houses):
                if is_vertical:
                    x = rect.center().x() - building_size // 2
                    y = rect.top() + 4 + i * (building_size + spacing)
                else:
                    x = rect.left() + 4 + i * (building_size + spacing)
                    y = rect.center().y() - building_size // 2
                
                painter.drawRect(x, y, building_size, building_size)
    
    def _draw_players(self, painter: QPainter) -> None:
        """Draw player tokens on the board."""
        if not self._game_state:
            return
        
        players = self._game_state.get("players", [])
        
        # Group players by position
        positions: dict[int, list[tuple[int, dict]]] = {}
        for i, player in enumerate(players):
            if player.get("state") == "BANKRUPT":
                continue
            pos = player.get("position", 0)
            if pos not in positions:
                positions[pos] = []
            positions[pos].append((i, player))
        
        # Draw players at each position
        for pos, player_list in positions.items():
            rect = self._get_space_rect(pos)
            token_size = 14
            
            for offset, (i, player) in enumerate(player_list):
                color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
                
                # Offset multiple players on same space
                x = rect.center().x() - token_size // 2 + offset * 6
                y = rect.center().y() - token_size // 2 + offset * 6
                
                # Draw token
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.GlobalColor.black, 2))
                painter.drawEllipse(x, y, token_size, token_size)
                
                # Highlight current player's token
                if player.get("id") == self._player_id:
                    painter.setPen(QPen(Qt.GlobalColor.white, 2))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(x - 2, y - 2, token_size + 4, token_size + 4)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse movement for hover effects."""
        pos = self._position_from_point(event.pos())
        
        if pos != self._hovered_space:
            self._hovered_space = pos
            self.update()
            
            # Show tooltip with space info
            if pos is not None:
                space_data = BOARD_SPACES.get(pos, {})
                name = space_data.get("name", f"Space {pos}")
                cost = space_data.get("cost")
                
                tooltip = name
                if cost:
                    tooltip += f"\nCost: ${cost}"
                
                # Add property info from game state
                if self._game_state:
                    prop_data = self._game_state.get("board", {}).get(str(pos))
                    if prop_data:
                        if prop_data.get("owner_id"):
                            # Find owner name
                            for p in self._game_state.get("players", []):
                                if p.get("id") == prop_data["owner_id"]:
                                    tooltip += f"\nOwner: {p.get('name', 'Unknown')}"
                                    break
                        if prop_data.get("houses", 0) > 0:
                            tooltip += f"\nHouses: {prop_data['houses']}"
                        if prop_data.get("has_hotel"):
                            tooltip += "\nHas Hotel"
                        if prop_data.get("is_mortgaged"):
                            tooltip += "\n(MORTGAGED)"
                
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
            else:
                QToolTip.hideText()
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse click on spaces."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._position_from_point(event.pos())
            if pos is not None:
                self.space_clicked.emit(pos)
    
    def leaveEvent(self, event) -> None:
        """Handle mouse leaving widget."""
        self._hovered_space = None
        self.update()
        QToolTip.hideText()
