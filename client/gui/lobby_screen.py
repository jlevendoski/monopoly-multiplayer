"""
Lobby screen for connecting and joining games.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QGroupBox, QMessageBox, QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from client.gui.styles import LOBBY_STYLESHEET


class LobbyScreen(QWidget):
    """
    Lobby screen with connect, game list, and game creation.
    
    Signals:
        connect_requested: User wants to connect (player_name)
        create_game_requested: User wants to create a game (game_name)
        join_game_requested: User wants to join a game (game_id)
        refresh_requested: User wants to refresh game list
        start_game_requested: Host wants to start the game
        leave_game_requested: User wants to leave current game
    """
    
    connect_requested = pyqtSignal(str)  # player_name
    create_game_requested = pyqtSignal(str)  # game_name
    join_game_requested = pyqtSignal(str)  # game_id
    refresh_requested = pyqtSignal()
    start_game_requested = pyqtSignal()
    leave_game_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lobbyWidget")
        self.setStyleSheet(LOBBY_STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("MONOPOLY")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Multiplayer Board Game")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Stacked widget for different states
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        
        # State 0: Connect form
        self._connect_widget = self._create_connect_widget()
        self._stack.addWidget(self._connect_widget)
        
        # State 1: Game browser
        self._browser_widget = self._create_browser_widget()
        self._stack.addWidget(self._browser_widget)
        
        # State 2: Waiting room
        self._waiting_widget = self._create_waiting_widget()
        self._stack.addWidget(self._waiting_widget)
        
        layout.addStretch()
        
        # Status bar
        self._status_label = QLabel("Not connected")
        self._status_label.setStyleSheet("color: #7F8C8D;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)
    
    def _create_connect_widget(self) -> QWidget:
        """Create the connection form."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Name input
        form = QGroupBox("Enter Your Name")
        form_layout = QVBoxLayout(form)
        
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Your name...")
        self._name_input.setMaxLength(20)
        self._name_input.returnPressed.connect(self._on_connect)
        form_layout.addWidget(self._name_input)
        
        self._connect_btn = QPushButton("Connect to Server")
        self._connect_btn.setObjectName("actionButton")
        self._connect_btn.clicked.connect(self._on_connect)
        form_layout.addWidget(self._connect_btn)
        
        layout.addWidget(form)
        
        return widget
    
    def _create_browser_widget(self) -> QWidget:
        """Create the game browser."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Create game section
        create_group = QGroupBox("Create New Game")
        create_layout = QHBoxLayout(create_group)
        
        self._game_name_input = QLineEdit()
        self._game_name_input.setPlaceholderText("Game name...")
        self._game_name_input.returnPressed.connect(self._on_create_game)
        create_layout.addWidget(self._game_name_input)
        
        create_btn = QPushButton("Create Game")
        create_btn.setObjectName("actionButton")
        create_btn.clicked.connect(self._on_create_game)
        create_layout.addWidget(create_btn)
        
        layout.addWidget(create_group)
        
        # Game list section
        list_group = QGroupBox("Join Existing Game")
        list_layout = QVBoxLayout(list_group)
        
        # Refresh button
        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        refresh_row.addWidget(refresh_btn)
        list_layout.addLayout(refresh_row)
        
        # Game list
        self._game_list = QListWidget()
        self._game_list.itemDoubleClicked.connect(self._on_game_double_clicked)
        list_layout.addWidget(self._game_list)
        
        # Join button
        join_btn = QPushButton("Join Selected Game")
        join_btn.clicked.connect(self._on_join_game)
        list_layout.addWidget(join_btn)
        
        layout.addWidget(list_group)
        
        return widget
    
    def _create_waiting_widget(self) -> QWidget:
        """Create the waiting room."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Game info
        info_group = QGroupBox("Game Lobby")
        info_layout = QVBoxLayout(info_group)
        
        self._game_info_label = QLabel("Waiting for players...")
        self._game_info_label.setFont(QFont("Arial", 14))
        self._game_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self._game_info_label)
        
        # Player list
        self._player_list = QListWidget()
        self._player_list.setMaximumHeight(200)
        info_layout.addWidget(self._player_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("Start Game")
        self._start_btn.setObjectName("actionButton")
        self._start_btn.clicked.connect(self.start_game_requested.emit)
        self._start_btn.setEnabled(False)
        btn_layout.addWidget(self._start_btn)
        
        leave_btn = QPushButton("Leave Game")
        leave_btn.setObjectName("dangerButton")
        leave_btn.clicked.connect(self.leave_game_requested.emit)
        btn_layout.addWidget(leave_btn)
        
        info_layout.addLayout(btn_layout)
        
        layout.addWidget(info_group)
        
        return widget
    
    def _on_connect(self) -> None:
        """Handle connect button click."""
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter your name")
            return
        self.connect_requested.emit(name)
    
    def _on_create_game(self) -> None:
        """Handle create game button click."""
        name = self._game_name_input.text().strip()
        if not name:
            name = f"{self._name_input.text()}'s Game"
        self.create_game_requested.emit(name)
    
    def _on_join_game(self) -> None:
        """Handle join game button click."""
        item = self._game_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Error", "Please select a game to join")
            return
        game_id = item.data(Qt.ItemDataRole.UserRole)
        if game_id:
            self.join_game_requested.emit(game_id)
    
    def _on_game_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on game in list."""
        game_id = item.data(Qt.ItemDataRole.UserRole)
        if game_id:
            self.join_game_requested.emit(game_id)
    
    # Public methods for updating state
    
    def show_connect_form(self) -> None:
        """Show the connect form."""
        self._stack.setCurrentIndex(0)
        self._status_label.setText("Not connected")
    
    def show_game_browser(self) -> None:
        """Show the game browser."""
        self._stack.setCurrentIndex(1)
        self._status_label.setText("Connected - Choose or create a game")
    
    def show_waiting_room(self, game_name: str, is_host: bool) -> None:
        """Show the waiting room."""
        self._stack.setCurrentIndex(2)
        self._game_info_label.setText(f"Game: {game_name}")
        self._start_btn.setVisible(is_host)
        self._status_label.setText("Waiting for players...")
    
    def update_game_list(self, games: list[dict]) -> None:
        """Update the list of available games."""
        self._game_list.clear()
        
        if not games:
            item = QListWidgetItem("No games available - create one!")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._game_list.addItem(item)
            return
        
        for game in games:
            text = f"{game.get('name', 'Unnamed')} ({game.get('player_count', 0)} players)"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, game.get("id"))
            self._game_list.addItem(item)
    
    def update_waiting_room(self, game_state: dict, is_host: bool) -> None:
        """Update the waiting room with current game state."""
        self._player_list.clear()
        
        players = game_state.get("players", [])
        for p in players:
            name = p.get("name", "Unknown")
            state = p.get("state", "")
            if state == "DISCONNECTED":
                name += " (disconnected)"
            self._player_list.addItem(name)
        
        # Enable start button if host and enough players
        self._start_btn.setEnabled(is_host and len(players) >= 2)
        self._start_btn.setVisible(is_host)
        
        self._status_label.setText(f"{len(players)} player(s) in lobby")
    
    def set_status(self, text: str) -> None:
        """Set the status message."""
        self._status_label.setText(text)
    
    def set_connecting(self, connecting: bool) -> None:
        """Set UI state during connection."""
        self._connect_btn.setEnabled(not connecting)
        self._name_input.setEnabled(not connecting)
        if connecting:
            self._connect_btn.setText("Connecting...")
            self._status_label.setText("Connecting to server...")
        else:
            self._connect_btn.setText("Connect to Server")
