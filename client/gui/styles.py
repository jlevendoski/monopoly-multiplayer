"""
Styles and colors for the Monopoly GUI.
"""

from PyQt6.QtGui import QColor

# Property group colors
PROPERTY_COLORS = {
    "BROWN": QColor(139, 69, 19),
    "LIGHT_BLUE": QColor(135, 206, 250),
    "PINK": QColor(255, 105, 180),
    "ORANGE": QColor(255, 165, 0),
    "RED": QColor(220, 20, 60),
    "YELLOW": QColor(255, 255, 0),
    "GREEN": QColor(34, 139, 34),
    "DARK_BLUE": QColor(0, 0, 139),
    "RAILROAD": QColor(128, 128, 128),
    "UTILITY": QColor(192, 192, 192),
}

# Player token colors
PLAYER_COLORS = [
    QColor(220, 20, 60),    # Red
    QColor(30, 144, 255),   # Blue
    QColor(50, 205, 50),    # Green
    QColor(255, 215, 0),    # Gold
    QColor(148, 0, 211),    # Purple
    QColor(255, 127, 80),   # Coral
]

# Space type colors
SPACE_COLORS = {
    "GO": QColor(144, 238, 144),
    "JAIL": QColor(255, 165, 0),
    "FREE_PARKING": QColor(200, 200, 200),
    "GO_TO_JAIL": QColor(255, 99, 71),
    "TAX": QColor(169, 169, 169),
    "CHANCE": QColor(255, 140, 0),
    "COMMUNITY_CHEST": QColor(100, 149, 237),
}

# UI Colors
BACKGROUND_COLOR = QColor(205, 230, 208)  # Light green board
BOARD_EDGE_COLOR = QColor(0, 100, 0)
TEXT_COLOR = QColor(0, 0, 0)
HIGHLIGHT_COLOR = QColor(255, 255, 0, 100)
MORTGAGED_OVERLAY = QColor(128, 128, 128, 180)

# Stylesheet
MAIN_STYLESHEET = """
QMainWindow {
    background-color: #2C3E50;
}

QWidget#centralWidget {
    background-color: #2C3E50;
}

QLabel {
    color: white;
}

QPushButton {
    background-color: #3498DB;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2980B9;
}

QPushButton:pressed {
    background-color: #1F618D;
}

QPushButton:disabled {
    background-color: #7F8C8D;
    color: #BDC3C7;
}

QPushButton#actionButton {
    background-color: #27AE60;
    font-size: 14px;
    padding: 12px 24px;
}

QPushButton#actionButton:hover {
    background-color: #229954;
}

QPushButton#dangerButton {
    background-color: #E74C3C;
}

QPushButton#dangerButton:hover {
    background-color: #C0392B;
}

QLineEdit {
    padding: 8px;
    border: 2px solid #3498DB;
    border-radius: 4px;
    background-color: white;
}

QListWidget {
    background-color: #34495E;
    color: white;
    border: 1px solid #3498DB;
    border-radius: 4px;
}

QListWidget::item {
    padding: 8px;
}

QListWidget::item:selected {
    background-color: #3498DB;
}

QListWidget::item:hover {
    background-color: #2C3E50;
}

QGroupBox {
    color: white;
    font-weight: bold;
    border: 2px solid #3498DB;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QScrollArea {
    border: none;
}

QTextEdit {
    background-color: #34495E;
    color: white;
    border: 1px solid #3498DB;
    border-radius: 4px;
}

QMessageBox {
    background-color: #2C3E50;
}

QMessageBox QLabel {
    color: white;
}

QDialog {
    background-color: #2C3E50;
}
"""

LOBBY_STYLESHEET = """
QWidget#lobbyWidget {
    background-color: #1A252F;
}

QLabel#titleLabel {
    font-size: 32px;
    font-weight: bold;
    color: #E74C3C;
}

QLabel#subtitleLabel {
    font-size: 16px;
    color: #BDC3C7;
}
"""
