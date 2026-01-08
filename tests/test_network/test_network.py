"""
Comprehensive test suite for the Monopoly network layer.

Tests the WebSocket server, connection management, game management,
message handling, and lobby protocol.

Run from project root: python -m pytest tests/test_network -v
Or run directly: python tests/test_network/test_network.py
"""

import asyncio
import json
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """ANSI color codes for pretty output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
    print(f" {text}")
    print(f"{'=' * 60}{Colors.RESET}\n")


def print_subheader(text: str) -> None:
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.RESET}")


def print_success(text: str) -> None:
    print(f"  {Colors.GREEN}✓ {text}{Colors.RESET}")


def print_failure(text: str) -> None:
    print(f"  {Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    print(f"  {Colors.YELLOW}→ {text}{Colors.RESET}")


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def add(self, passed: bool) -> None:
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def summary(self) -> None:
        print_header("TEST SUMMARY")
        total = self.passed + self.failed
        print(f"  Total:  {total}")
        print(f"  {Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.failed}{Colors.RESET}")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed ✗{Colors.RESET}")


def assert_test(condition: bool, success_msg: str, failure_msg: str) -> bool:
    if condition:
        print_success(success_msg)
        return True
    else:
        print_failure(failure_msg)
        return False


# =============================================================================
# Mock WebSocket for unit tests
# =============================================================================

class MockWebSocket:
    """Mock WebSocket for testing without real connections."""
    
    def __init__(self, id: str):
        self.id = id
        self.sent_messages = []
        self.closed = False
    
    async def send(self, data: str) -> None:
        if self.closed:
            raise Exception("Connection closed")
        self.sent_messages.append(data)
    
    async def recv(self) -> str:
        raise NotImplementedError("Use real WebSocket for recv tests")
    
    async def close(self) -> None:
        self.closed = True
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return isinstance(other, MockWebSocket) and self.id == other.id
    
    def get_messages(self) -> list[dict]:
        return [json.loads(m) for m in self.sent_messages]
    
    def clear_messages(self) -> None:
        self.sent_messages.clear()


# =============================================================================
# Test Functions
# =============================================================================

def test_connection_manager() -> bool:
    """Test ConnectionManager functionality."""
    print_header("CONNECTION MANAGER TESTS")
    results = TestResults()
    
    async def run_tests():
        from server.network.connection_manager import ConnectionManager
        
        cm = ConnectionManager()
        
        print_subheader("Connection Lifecycle")
        
        ws1 = MockWebSocket("ws1")
        ws2 = MockWebSocket("ws2")
        
        # Connect players
        conn1 = await cm.connect(ws1, "player-1", "Alice")
        conn2 = await cm.connect(ws2, "player-2", "Bob")
        
        results.add(assert_test(
            conn1.player_id == "player-1" and conn1.player_name == "Alice",
            "Player 1 connected with correct data",
            "Player 1 connection data incorrect"
        ))
        
        results.add(assert_test(
            cm.is_player_connected("player-1") and cm.is_player_connected("player-2"),
            "Both players show as connected",
            "Connection status incorrect"
        ))
        
        print_subheader("Game Association")
        
        # Join game
        result = await cm.join_game("player-1", "game-1", is_host=True)
        results.add(assert_test(
            result and cm.get_game_id("player-1") == "game-1",
            "Player 1 joined game as host",
            "Failed to join game"
        ))
        
        await cm.join_game("player-2", "game-1")
        players = cm.get_players_in_game("game-1")
        results.add(assert_test(
            len(players) == 2,
            f"Game has 2 players: {players}",
            f"Wrong player count: {len(players)}"
        ))
        
        # Get host
        host = cm.get_host("game-1")
        results.add(assert_test(
            host is not None and host.player_id == "player-1",
            "Correct host identified",
            "Host lookup failed"
        ))
        
        print_subheader("Messaging")
        
        from shared.protocol import Message
        from shared.enums import MessageType
        
        msg = Message(type=MessageType.GAME_STATE, data={"test": True})
        
        # Send to player
        result = await cm.send_to_player("player-1", msg)
        results.add(assert_test(
            result and len(ws1.sent_messages) == 1,
            "Message sent to player 1",
            "Failed to send message"
        ))
        
        # Broadcast to game
        ws1.clear_messages()
        count = await cm.broadcast_to_game("game-1", msg)
        results.add(assert_test(
            count == 2,
            f"Broadcast sent to {count} players",
            f"Broadcast count wrong: {count}"
        ))
        
        # Broadcast with exclusion
        ws1.clear_messages()
        ws2.clear_messages()
        count = await cm.broadcast_to_game("game-1", msg, exclude_player_id="player-1")
        results.add(assert_test(
            count == 1 and len(ws1.sent_messages) == 0 and len(ws2.sent_messages) == 1,
            "Broadcast with exclusion works",
            "Exclusion failed"
        ))
        
        print_subheader("Disconnect/Reconnect")
        
        # Disconnect
        disconnected = await cm.disconnect(ws1)
        results.add(assert_test(
            disconnected is not None and not cm.is_player_connected("player-1"),
            "Player 1 disconnected",
            "Disconnect failed"
        ))
        
        results.add(assert_test(
            cm.is_player_in_game("player-1", "game-1"),
            "Disconnected player still in game (awaiting reconnect)",
            "Player removed from game on disconnect"
        ))
        
        # Reconnect
        ws1_new = MockWebSocket("ws1-new")
        conn1_new = await cm.connect(ws1_new, "player-1", "Alice")
        results.add(assert_test(
            conn1_new.game_id == "game-1" and conn1_new.is_host,
            "Reconnection restored game and host status",
            "Reconnection failed to restore state"
        ))
        
        print_subheader("Host Transfer")
        
        result = await cm.transfer_host("game-1", "player-2")
        new_host = cm.get_host("game-1")
        results.add(assert_test(
            result and new_host.player_id == "player-2",
            "Host transferred to player 2",
            "Host transfer failed"
        ))
        
        return results.failed == 0
    
    return asyncio.run(run_tests())


def test_game_manager() -> bool:
    """Test GameManager functionality."""
    print_header("GAME MANAGER TESTS")
    results = TestResults()
    
    # Set up temp database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    os.environ["DATABASE_PATH"] = temp_db.name
    
    try:
        from server.network.game_manager import GameManager
        from server.persistence import init_database, GameRepository
        from shared.protocol import GameSettings
        from shared.enums import GamePhase
        
        db = init_database(temp_db.name)
        repo = GameRepository(db)
        gm = GameManager(repo)
        
        print_subheader("Game Creation")
        
        success, msg, managed = gm.create_game(
            name="Test Game",
            host_player_id="host-1",
            host_player_name="Alice",
            settings=GameSettings(allow_spectators=True, max_players=4)
        )
        
        results.add(assert_test(
            success and managed is not None,
            f"Game created: {managed.game_id if managed else 'N/A'}",
            f"Failed to create game: {msg}"
        ))
        
        results.add(assert_test(
            managed.host_player_id == "host-1",
            "Host correctly set",
            "Host not set correctly"
        ))
        
        # Duplicate game prevention
        success, msg, _ = gm.create_game("Another", "host-1", "Alice")
        results.add(assert_test(
            not success,
            f"Prevented host from creating second game: {msg}",
            "Allowed duplicate game creation"
        ))
        
        print_subheader("Joining Games")
        
        game_id = managed.game_id
        
        success, msg, player = gm.join_game(game_id, "player-2", "Bob")
        results.add(assert_test(
            success and player is not None,
            f"Player joined game: {msg}",
            f"Failed to join: {msg}"
        ))
        
        # Spectator join
        success, msg, _ = gm.join_game(game_id, "spectator-1", "Charlie", as_spectator=True)
        results.add(assert_test(
            success,
            "Spectator joined game",
            f"Spectator failed to join: {msg}"
        ))
        
        print_subheader("Starting Games")
        
        # Non-host cannot start
        success, msg = gm.start_game(game_id, "player-2")
        results.add(assert_test(
            not success,
            f"Non-host blocked from starting: {msg}",
            "Non-host allowed to start"
        ))
        
        # Host can start
        success, msg = gm.start_game(game_id, "host-1")
        results.add(assert_test(
            success and managed.is_started,
            "Host started game",
            f"Failed to start: {msg}"
        ))
        
        print_subheader("Save/Load")
        
        # Make changes
        managed.game.turn_number = 10
        player = managed.game.players.get("host-1")
        if player:
            player.money = 999
        
        # Save
        success, msg = gm.save_game(game_id)
        results.add(assert_test(
            success,
            "Game saved",
            f"Save failed: {msg}"
        ))
        
        # Clear from memory
        del gm._games[game_id]
        for pid in list(gm._player_games.keys()):
            if gm._player_games[pid] == game_id:
                del gm._player_games[pid]
        
        # Load
        success, msg, loaded = gm.load_game(game_id)
        results.add(assert_test(
            success and loaded is not None,
            "Game loaded",
            f"Load failed: {msg}"
        ))
        
        results.add(assert_test(
            loaded.game.turn_number == 10,
            "Turn number preserved",
            f"Turn number wrong: {loaded.game.turn_number}"
        ))
        
        print_subheader("Listing Games")
        
        # Create another game
        gm.create_game("Second Game", "host-2", "Dave")
        
        games = gm.list_games()
        results.add(assert_test(
            len(games) >= 2,
            f"Listed {len(games)} games",
            f"Wrong game count: {len(games)}"
        ))
        
        joinable = gm.list_joinable_games()
        results.add(assert_test(
            len(joinable) >= 1,
            f"Found {len(joinable)} joinable games",
            "No joinable games found"
        ))
        
        print_subheader("Leave Game")
        
        success, msg, left_id = gm.leave_game("player-2")
        results.add(assert_test(
            success and left_id == game_id,
            "Player left game",
            f"Leave failed: {msg}"
        ))
        
        return results.failed == 0
        
    finally:
        os.unlink(temp_db.name)


def test_message_handler() -> bool:
    """Test MessageHandler functionality."""
    print_header("MESSAGE HANDLER TESTS")
    results = TestResults()
    
    # Set up temp database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    os.environ["DATABASE_PATH"] = temp_db.name
    
    try:
        async def run_tests():
            from server.network import ConnectionManager, GameManager, MessageHandler
            from server.persistence import init_database, GameRepository
            from shared.protocol import Message
            from shared.enums import MessageType, GamePhase
            
            db = init_database(temp_db.name)
            repo = GameRepository(db)
            connections = ConnectionManager()
            games = GameManager(repo)
            handler = MessageHandler(games, connections)
            
            # Set up mock connections
            ws1 = MockWebSocket("ws1")
            ws2 = MockWebSocket("ws2")
            await connections.connect(ws1, "player-1", "Alice")
            await connections.connect(ws2, "player-2", "Bob")
            
            print_subheader("Lobby Messages")
            
            # List games (empty)
            result = await handler.handle_message("player-1", {
                "type": "LIST_GAMES",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_LIST,
                "LIST_GAMES returns game list",
                f"Wrong response type: {result.response.type}"
            ))
            
            # Create game
            result = await handler.handle_message("player-1", {
                "type": "CREATE_GAME",
                "data": {"game_name": "Test", "player_name": "Alice"},
                "request_id": "req-1"
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_STATE,
                "CREATE_GAME returns game state",
                f"Wrong response: {result.response.type}"
            ))
            results.add(assert_test(
                result.response.request_id == "req-1",
                "Request ID preserved in response",
                "Request ID not preserved"
            ))
            
            game_id = result.response.data.get("game_id")
            
            # Join game
            result = await handler.handle_message("player-2", {
                "type": "JOIN_GAME",
                "data": {"game_id": game_id, "player_name": "Bob"}
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_STATE and result.broadcasts,
                "JOIN_GAME returns state and broadcasts",
                "Join response incorrect"
            ))
            
            print_subheader("Host Privileges")
            
            # Non-host cannot start
            result = await handler.handle_message("player-2", {
                "type": "START_GAME",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.ERROR,
                "Non-host blocked from starting",
                "Non-host allowed to start"
            ))
            
            # Host can start
            result = await handler.handle_message("player-1", {
                "type": "START_GAME",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_STATE and result.should_save,
                "Host started game, save triggered",
                f"Start failed: {result.response.type}"
            ))
            
            # Transfer host
            result = await handler.handle_message("player-1", {
                "type": "TRANSFER_HOST",
                "data": {"player_id": "player-2"}
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_STATE,
                "Host transfer succeeded",
                f"Transfer failed: {result.response.data if result.response.type == MessageType.ERROR else ''}"
            ))
            
            print_subheader("Game Actions")
            
            # Determine whose turn
            managed = games.get_game(game_id)
            current_id = managed.game.current_player.id
            other_id = "player-1" if current_id == "player-2" else "player-2"
            
            # Wrong player cannot roll
            result = await handler.handle_message(other_id, {
                "type": "ROLL_DICE",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.ERROR,
                "Wrong player blocked from rolling",
                "Wrong player allowed to roll"
            ))
            
            # Correct player can roll
            result = await handler.handle_message(current_id, {
                "type": "ROLL_DICE",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_STATE and result.broadcasts,
                "Dice roll succeeded with broadcasts",
                f"Roll failed: {result.response.type}"
            ))
            
            dice_broadcast = result.broadcasts[0]
            results.add(assert_test(
                dice_broadcast.type == MessageType.DICE_ROLLED,
                f"Dice broadcast: {dice_broadcast.data['die1']} + {dice_broadcast.data['die2']}",
                "No dice broadcast"
            ))
            
            print_subheader("State Query")
            
            result = await handler.handle_message("player-1", {
                "type": "GAME_STATE",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.GAME_STATE and "players" in result.response.data,
                "State query returns full state",
                "State query failed"
            ))
            
            print_subheader("Error Handling")
            
            # Invalid JSON
            result = await handler.handle_message("player-1", "not valid json")
            results.add(assert_test(
                result.response.type == MessageType.ERROR,
                "Invalid JSON handled gracefully",
                "Invalid JSON not caught"
            ))
            
            # Unknown message type
            result = await handler.handle_message("player-1", {
                "type": "AUCTION_BID",
                "data": {}
            })
            results.add(assert_test(
                result.response.type == MessageType.ERROR,
                "Unknown message type handled",
                "Unknown type not caught"
            ))
            
            return results.failed == 0
        
        return asyncio.run(run_tests())
        
    finally:
        os.unlink(temp_db.name)


def test_protocol() -> bool:
    """Test protocol message serialization."""
    print_header("PROTOCOL TESTS")
    results = TestResults()
    
    from shared.protocol import (
        Message, ErrorMessage, CreateGameRequest, JoinGameRequest,
        DiceRolledMessage, GameSettings, parse_message
    )
    from shared.enums import MessageType
    
    print_subheader("Message Serialization")
    
    # Basic message
    msg = Message(type=MessageType.ROLL_DICE, data={"test": 123}, request_id="req-1")
    json_str = msg.to_json()
    parsed = parse_message(json_str)
    
    results.add(assert_test(
        parsed.type == MessageType.ROLL_DICE and parsed.request_id == "req-1",
        "Message round-trips correctly",
        "Message serialization failed"
    ))
    
    print_subheader("Request Messages")
    
    # Create game request
    req = CreateGameRequest.create(
        game_name="My Game",
        player_name="Alice",
        settings={"max_players": 6}
    )
    results.add(assert_test(
        req.type == MessageType.CREATE_GAME and req.data["game_name"] == "My Game",
        "CreateGameRequest created correctly",
        "CreateGameRequest incorrect"
    ))
    
    # Join game request
    req = JoinGameRequest.create(game_id="game-123", player_name="Bob")
    results.add(assert_test(
        req.type == MessageType.JOIN_GAME and req.data["game_id"] == "game-123",
        "JoinGameRequest created correctly",
        "JoinGameRequest incorrect"
    ))
    
    print_subheader("Response Messages")
    
    # Error message
    err = ErrorMessage.create("Test error", "TEST_CODE", "req-123")
    results.add(assert_test(
        err.type == MessageType.ERROR and err.data["code"] == "TEST_CODE",
        "ErrorMessage created correctly",
        "ErrorMessage incorrect"
    ))
    
    # Dice rolled message
    dice = DiceRolledMessage.create(
        player_id="p1", player_name="Alice",
        die1=3, die2=4, total=7, is_double=False,
        result_message="Landed on Go"
    )
    results.add(assert_test(
        dice.type == MessageType.DICE_ROLLED and dice.data["total"] == 7,
        "DiceRolledMessage created correctly",
        "DiceRolledMessage incorrect"
    ))
    
    print_subheader("Game Settings")
    
    settings = GameSettings(allow_spectators=True, max_players=6)
    data = settings.to_dict()
    loaded = GameSettings.from_dict(data)
    
    results.add(assert_test(
        loaded.allow_spectators == True and loaded.max_players == 6,
        "GameSettings round-trips correctly",
        "GameSettings serialization failed"
    ))
    
    return results.failed == 0


def test_integration() -> bool:
    """Integration test with real WebSocket server."""
    print_header("INTEGRATION TESTS")
    results = TestResults()
    
    # Set up temp database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    os.environ["DATABASE_PATH"] = temp_db.name
    
    try:
        import websockets
        from server.network.server import MonopolyServer
        
        async def run_tests():
            server = MonopolyServer(host="127.0.0.1", port=18767, db_path=temp_db.name)
            server_task = asyncio.create_task(server.start())
            await asyncio.sleep(0.5)
            
            try:
                print_subheader("Client Connection")
                
                ws1 = await websockets.connect("ws://127.0.0.1:18767")
                await ws1.send(json.dumps({
                    "type": "CONNECT",
                    "data": {"player_id": "alice-1", "player_name": "Alice"}
                }))
                response = json.loads(await ws1.recv())
                
                results.add(assert_test(
                    response["data"]["success"],
                    "Client 1 connected",
                    "Client 1 connection failed"
                ))
                
                ws2 = await websockets.connect("ws://127.0.0.1:18767")
                await ws2.send(json.dumps({
                    "type": "CONNECT",
                    "data": {"player_id": "bob-2", "player_name": "Bob"}
                }))
                response = json.loads(await ws2.recv())
                
                results.add(assert_test(
                    response["data"]["success"],
                    "Client 2 connected",
                    "Client 2 connection failed"
                ))
                
                print_subheader("Game Flow")
                
                # Create game
                await ws1.send(json.dumps({
                    "type": "CREATE_GAME",
                    "data": {"game_name": "Integration Test", "player_name": "Alice"}
                }))
                response = json.loads(await ws1.recv())
                game_id = response["data"]["game_id"]
                
                results.add(assert_test(
                    game_id is not None,
                    f"Game created: {game_id[:8]}...",
                    "Game creation failed"
                ))
                
                # Join game
                await ws2.send(json.dumps({
                    "type": "JOIN_GAME",
                    "data": {"game_id": game_id, "player_name": "Bob"}
                }))
                
                await asyncio.sleep(0.3)
                
                # Drain messages
                async def drain(ws, timeout=0.3):
                    msgs = []
                    while True:
                        try:
                            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout))
                            msgs.append(msg)
                        except asyncio.TimeoutError:
                            break
                    return msgs
                
                bob_msgs = await drain(ws2)
                alice_msgs = await drain(ws1)
                
                results.add(assert_test(
                    any(m["type"] == "GAME_STATE" for m in bob_msgs),
                    "Bob received game state",
                    "Bob didn't receive state"
                ))
                
                results.add(assert_test(
                    any(m["type"] == "JOIN_GAME" for m in alice_msgs),
                    "Alice notified of Bob joining",
                    "Alice not notified"
                ))
                
                # Start game
                await ws1.send(json.dumps({"type": "START_GAME", "data": {}}))
                await asyncio.sleep(0.3)
                
                alice_msgs = await drain(ws1)
                bob_msgs = await drain(ws2)
                
                results.add(assert_test(
                    any(m["type"] == "GAME_STARTED" for m in bob_msgs),
                    "Game started, Bob notified",
                    "Game start notification missing"
                ))
                
                print_subheader("Disconnect/Reconnect")
                
                await ws2.close()
                await asyncio.sleep(0.3)
                
                alice_msgs = await drain(ws1)
                results.add(assert_test(
                    any(m["type"] == "DISCONNECT" for m in alice_msgs),
                    "Alice notified of Bob's disconnect",
                    "Disconnect notification missing"
                ))
                
                # Reconnect
                ws2_new = await websockets.connect("ws://127.0.0.1:18767")
                await ws2_new.send(json.dumps({
                    "type": "CONNECT",
                    "data": {"player_id": "bob-2", "player_name": "Bob"}
                }))
                
                await asyncio.sleep(0.3)
                bob_msgs = await drain(ws2_new)
                
                connect_msg = next((m for m in bob_msgs if m["type"] == "CONNECT"), None)
                results.add(assert_test(
                    connect_msg and connect_msg["data"]["reconnected_to_game"] == game_id,
                    "Bob reconnected to game",
                    "Reconnection failed"
                ))
                
                state_msg = next((m for m in bob_msgs if m["type"] == "GAME_STATE"), None)
                results.add(assert_test(
                    state_msg is not None,
                    "Bob received game state on reconnect",
                    "No state on reconnect"
                ))
                
                print_subheader("Server Stats")
                
                stats = server.get_stats()
                results.add(assert_test(
                    stats["connections"]["total_connections"] == 2,
                    f"Server tracking 2 connections",
                    f"Wrong connection count: {stats}"
                ))
                
                await ws1.close()
                await ws2_new.close()
                
            finally:
                await server.stop()
            
            return results.failed == 0
        
        return asyncio.run(run_tests())
        
    except ImportError:
        print_info("Skipping integration tests (websockets not installed)")
        return True
    finally:
        os.unlink(temp_db.name)


def run_all_tests() -> bool:
    """Run all test suites."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           MONOPOLY NETWORK LAYER TEST SUITE              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    all_results = TestResults()
    
    tests = [
        ("Protocol", test_protocol),
        ("Connection Manager", test_connection_manager),
        ("Game Manager", test_game_manager),
        ("Message Handler", test_message_handler),
        ("Integration", test_integration),
    ]
    
    for name, test_func in tests:
        try:
            passed = test_func()
            all_results.add(passed)
        except Exception as e:
            print_failure(f"{name} tests raised exception: {e}")
            import traceback
            traceback.print_exc()
            all_results.add(False)
    
    all_results.summary()
    
    return all_results.failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
