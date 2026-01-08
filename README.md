# Monopoly Multiplayer

A multiplayer Monopoly clone with a central server and PyQt6-based client GUI.

## Project Structure

```
Monopoly/
├── client/                 # Client application
│   ├── gui/               # PyQt6 GUI components
│   │   ├── widgets/       # Reusable widgets (board, panels, dialogs)
│   │   ├── lobby_screen.py
│   │   ├── game_screen.py
│   │   └── main_window.py
│   ├── network/           # WebSocket client
│   └── main.py           # Client entry point
│
├── server/                # Server application
│   ├── game_engine/      # Core game logic
│   ├── network/          # WebSocket server & message handling
│   ├── persistence/      # SQLite database layer
│   └── main.py          # Server entry point
│
├── shared/               # Shared code (client & server)
│   ├── constants.py     # Board data, game constants
│   ├── enums.py         # Enumerations
│   └── protocol.py      # Message definitions
│
└── tests/               # Test suites
```

## Installation

### Server

```bash
pip install -r requirements-server.txt
```

### Client

```bash
pip install -r requirements-client.txt
```

### Development (both + testing)

```bash
pip install -r requirements-dev.txt
```

## Running

### Option 1: Local Game (Offline)

Play on a single device with friends taking turns (hot-seat multiplayer):

```bash
python -m client.local.local_main
```

No server needed! Players pass the device between turns.

### Option 2: Online Multiplayer

#### Start the Server

```bash
python -m server.main
```

The server starts on `ws://localhost:8765` by default.

Configure via environment variables (or `.env` file):
- `SERVER_HOST` - Server bind address (default: 0.0.0.0)
- `SERVER_PORT` - Server port (default: 8765)
- `DATABASE_PATH` - SQLite database path (default: ./data/monopoly.db)
- `LOG_LEVEL` - Logging level (default: INFO)
- `SERVER_SECRET_KEY` - Secret key for sessions (change in production!)

#### Start the Client

```bash
python -m client.main
```

Configure via environment variables:
- `MONOPOLY_SERVER_HOST` - Server host (default: localhost)
- `MONOPOLY_SERVER_PORT` - Server port (default: 8765)
- `MONOPOLY_WINDOW_WIDTH` - Window width (default: 1280)
- `MONOPOLY_WINDOW_HEIGHT` - Window height (default: 800)

### GUI Test Mode

Test the GUI without playing a full game:

```bash
python -m tests.test_gui.test_gui
```

This opens a test window with controls to manipulate game state and see how the UI responds.

## How to Play

1. **Start the server** in one terminal
2. **Start clients** in separate terminals (one per player)
3. **Connect** - Enter your name and click "Connect to Server"
4. **Create or Join a Game** - One player creates a game, others join
5. **Start the Game** - Host clicks "Start Game" when 2-4 players have joined
6. **Play!** - Roll dice, buy properties, build houses, and bankrupt your opponents

## Game Rules

Standard Monopoly rules with house rule modifications:
- **No auctions** - If you decline to buy a property, it stays unowned
- 2-4 players
- $1500 starting money
- $200 for passing GO
- $50 jail bail

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Or run individual test suites
python -m tests.test_game_engine.test_game_engine
python -m tests.test_network.test_network
python -m tests.test_persistence.test_persistence
```

## Architecture

### Client-Server Communication

All communication uses WebSocket with JSON messages. The protocol is defined in `shared/protocol.py`.

Message flow:
1. Client connects with `CONNECT` message
2. Client creates/joins game with `CREATE_GAME`/`JOIN_GAME`
3. Host starts game with `START_GAME`
4. Players take turns with `ROLL_DICE`, `BUY_PROPERTY`, `END_TURN`, etc.
5. Server broadcasts game events to all players

### Game State

The server maintains authoritative game state. Clients receive state updates and display them. All validation happens server-side.

### Persistence

Games are automatically saved to SQLite. Players can reconnect to ongoing games if disconnected.

## Customization

### Adding Images

The GUI uses placeholder graphics. To add custom images:

1. Board spaces: Modify `BoardWidget._draw_space()` in `client/gui/widgets/board_widget.py`
2. Property cards: Modify `PropertyDialog` in `client/gui/widgets/property_dialog.py`
3. Player tokens: Modify `BoardWidget._draw_players()`

### Renaming Properties

Edit `shared/constants.py` - the `PROPERTIES` list contains all board space definitions.

### Changing Colors

Edit `client/gui/styles.py` for all color definitions.
