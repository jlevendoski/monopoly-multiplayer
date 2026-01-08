#!/usr/bin/env python3
"""
Terminal-based test client for Monopoly server.

Usage:
    python test_client.py [--host HOST] [--port PORT] [--name NAME]

This provides an interactive CLI to test the server without needing PyQt6.
"""

import asyncio
import json
import os
import sys
import uuid
import argparse
from typing import Optional

import websockets
from websockets.client import WebSocketClientProtocol

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.enums import MessageType
from shared.constants import BOARD_SPACES


class TerminalClient:
    """Simple terminal-based Monopoly client for testing."""
    
    def __init__(self, host: str, port: int, player_name: str):
        self.host = host
        self.port = port
        self.player_name = player_name
        self.player_id = str(uuid.uuid4())
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.game_id: Optional[str] = None
        self.game_state: Optional[dict] = None
        self.running = True
    
    @property
    def server_url(self) -> str:
        return f"ws://{self.host}:{self.port}"
    
    async def connect(self) -> bool:
        """Connect to the server."""
        try:
            print(f"Connecting to {self.server_url}...")
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=30,
                ping_timeout=10,
            )
            
            # Send CONNECT message
            connect_msg = {
                "type": MessageType.CONNECT.value,
                "data": {
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                }
            }
            await self.websocket.send(json.dumps(connect_msg))
            
            # Wait for response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
            data = json.loads(response)
            
            if data.get("type") == MessageType.CONNECT.value and data.get("data", {}).get("success"):
                print(f"✓ Connected as {self.player_name} (ID: {self.player_id[:8]}...)")
                reconnected = data.get("data", {}).get("reconnected_to_game")
                if reconnected:
                    self.game_id = reconnected
                    print(f"  Reconnected to game: {reconnected}")
                return True
            else:
                print(f"✗ Connection rejected: {data}")
                return False
                
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    async def send_and_receive(self, msg_type: str, data: dict = None) -> dict:
        """Send a message and wait for response."""
        request_id = str(uuid.uuid4())
        message = {
            "type": msg_type,
            "request_id": request_id,
            "data": data or {}
        }
        
        await self.websocket.send(json.dumps(message))
        
        # Wait for response with matching request_id or relevant message
        while True:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
            resp_data = json.loads(response)
            
            # Check if it's our response
            if resp_data.get("request_id") == request_id:
                return resp_data
            
            # Handle broadcasts/state updates
            if resp_data.get("type") == MessageType.GAME_STATE.value:
                self.game_state = resp_data.get("data")
                self.game_id = self.game_state.get("game_id")
                return resp_data
            
            # Print other messages
            self._print_message(resp_data)
    
    def _print_message(self, data: dict) -> None:
        """Print a received message nicely."""
        msg_type = data.get("type", "unknown")
        msg_data = data.get("data", {})
        
        if msg_type == MessageType.PLAYER_JOINED.value:
            print(f"  → Player joined: {msg_data.get('player_name')}")
        elif msg_type == MessageType.PLAYER_LEFT.value:
            print(f"  → Player left: {msg_data.get('player_name')}")
        elif msg_type == MessageType.PLAYER_DISCONNECTED.value:
            print(f"  → Player disconnected: {msg_data.get('player_name')}")
        elif msg_type == MessageType.PLAYER_RECONNECTED.value:
            print(f"  → Player reconnected: {msg_data.get('player_name')}")
        elif msg_type == MessageType.ERROR.value:
            print(f"  ✗ Error: {msg_data.get('message')} ({msg_data.get('code')})")
        else:
            print(f"  → {msg_type}: {json.dumps(msg_data, indent=2)[:200]}")
    
    def _print_game_state(self) -> None:
        """Print current game state nicely."""
        if not self.game_state:
            print("No game state available")
            return
        
        print("\n" + "=" * 60)
        print(f"Game: {self.game_state.get('game_name', 'Unknown')} ({self.game_id})")
        print(f"Status: {self.game_state.get('status', 'unknown')}")
        
        players = self.game_state.get('players', [])
        current_idx = self.game_state.get('current_player_index', 0)
        
        print(f"\nPlayers ({len(players)}):")
        for i, p in enumerate(players):
            marker = "→ " if i == current_idx else "  "
            pos = p.get('position', 0)
            space_name = BOARD_SPACES.get(pos, {}).get('name', f'Space {pos}')
            jail_str = " [IN JAIL]" if p.get('is_in_jail') else ""
            bankrupt_str = " [BANKRUPT]" if p.get('is_bankrupt') else ""
            print(f"{marker}{p.get('name', '?')}: ${p.get('money', 0)} at {space_name} (pos {pos}){jail_str}{bankrupt_str}")
        
        # Show properties owned by current player
        my_player = next((p for p in players if p.get('id') == self.player_id), None)
        if my_player:
            props = my_player.get('properties', [])
            if props:
                print(f"\nYour properties:")
                for pos in props:
                    space = BOARD_SPACES.get(pos, {})
                    print(f"  - {space.get('name', f'Position {pos}')} ({space.get('group', 'N/A')})")
        
        turn_state = self.game_state.get('turn_state', {})
        if turn_state:
            print(f"\nTurn state: {turn_state.get('phase', 'unknown')}")
            if turn_state.get('dice_roll'):
                print(f"  Last roll: {turn_state.get('dice_roll')}")
            if turn_state.get('can_buy_property'):
                print(f"  Can buy property at current position")
        
        print("=" * 60 + "\n")
    
    async def run_interactive(self) -> None:
        """Run interactive command loop."""
        print("\n" + "=" * 60)
        print("MONOPOLY TEST CLIENT")
        print("=" * 60)
        print("\nCommands:")
        print("  list          - List available games")
        print("  create <name> - Create a new game")
        print("  join <id>     - Join a game by ID")
        print("  leave         - Leave current game")
        print("  start         - Start the game (host only)")
        print("  roll          - Roll dice")
        print("  buy           - Buy current property")
        print("  decline       - Decline to buy")
        print("  end           - End your turn")
        print("  state         - Show current game state")
        print("  bail          - Pay bail ($50)")
        print("  quit          - Disconnect and exit")
        print("=" * 60 + "\n")
        
        # Start background listener for broadcasts
        listener_task = asyncio.create_task(self._listen_for_broadcasts())
        
        try:
            while self.running:
                try:
                    cmd = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input(f"[{self.player_name}]> ").strip()
                    )
                except EOFError:
                    break
                
                if not cmd:
                    continue
                
                parts = cmd.split(maxsplit=1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else None
                
                await self._handle_command(command, arg)
                
        finally:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
    
    async def _listen_for_broadcasts(self) -> None:
        """Background task to listen for server broadcasts."""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=0.5)
                    data = json.loads(message)
                    
                    if data.get("type") == MessageType.GAME_STATE.value:
                        self.game_state = data.get("data")
                        self.game_id = self.game_state.get("game_id")
                        print("\n  [Game state updated]")
                    else:
                        self._print_message(data)
                        
                except asyncio.TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    print("\n  [Connection closed by server]")
                    self.running = False
                    break
        except asyncio.CancelledError:
            pass
    
    async def _handle_command(self, command: str, arg: Optional[str]) -> None:
        """Handle a user command."""
        try:
            if command == "quit":
                self.running = False
                await self.websocket.close()
                print("Disconnected.")
                
            elif command == "list":
                response = await self.send_and_receive(MessageType.LIST_GAMES.value)
                games = response.get("data", {}).get("games", [])
                if games:
                    print("\nAvailable games:")
                    for g in games:
                        print(f"  {g.get('id', '?')[:8]}... - {g.get('name', 'Unnamed')} ({g.get('player_count', 0)} players, {g.get('status', '?')})")
                else:
                    print("No games available. Create one with 'create <name>'")
                    
            elif command == "create":
                name = arg or f"{self.player_name}'s Game"
                response = await self.send_and_receive(
                    MessageType.CREATE_GAME.value,
                    {"game_name": name, "player_name": self.player_name}
                )
                if response.get("type") == MessageType.GAME_STATE.value:
                    print(f"✓ Created game: {name}")
                    self._print_game_state()
                else:
                    print(f"✗ Failed to create game: {response}")
                    
            elif command == "join":
                if not arg:
                    print("Usage: join <game_id>")
                    return
                response = await self.send_and_receive(
                    MessageType.JOIN_GAME.value,
                    {"game_id": arg, "player_name": self.player_name}
                )
                if response.get("type") == MessageType.GAME_STATE.value:
                    print(f"✓ Joined game")
                    self._print_game_state()
                else:
                    print(f"✗ Failed to join game: {response}")
                    
            elif command == "leave":
                response = await self.send_and_receive(MessageType.LEAVE_GAME.value)
                if response.get("data", {}).get("success"):
                    print("✓ Left game")
                    self.game_id = None
                    self.game_state = None
                else:
                    print(f"✗ Failed to leave: {response}")
                    
            elif command == "start":
                response = await self.send_and_receive(MessageType.START_GAME.value)
                if response.get("type") == MessageType.GAME_STATE.value:
                    print("✓ Game started!")
                    self._print_game_state()
                else:
                    print(f"✗ Failed to start: {response}")
                    
            elif command == "roll":
                response = await self.send_and_receive(MessageType.ROLL_DICE.value)
                if response.get("type") == MessageType.GAME_STATE.value:
                    dice = response.get("data", {}).get("turn_state", {}).get("dice_roll", [])
                    print(f"✓ Rolled: {dice} (total: {sum(dice) if dice else 0})")
                    self._print_game_state()
                else:
                    print(f"✗ Failed to roll: {response}")
                    
            elif command == "buy":
                response = await self.send_and_receive(MessageType.BUY_PROPERTY.value)
                if response.get("type") == MessageType.GAME_STATE.value:
                    print("✓ Property purchased!")
                    self._print_game_state()
                else:
                    print(f"✗ Failed to buy: {response}")
                    
            elif command == "decline":
                response = await self.send_and_receive(MessageType.DECLINE_PROPERTY.value)
                if response.get("type") == MessageType.GAME_STATE.value:
                    print("✓ Declined property")
                    self._print_game_state()
                else:
                    print(f"✗ Failed: {response}")
                    
            elif command == "end":
                response = await self.send_and_receive(MessageType.END_TURN.value)
                if response.get("type") == MessageType.GAME_STATE.value:
                    print("✓ Turn ended")
                    self._print_game_state()
                else:
                    print(f"✗ Failed to end turn: {response}")
                    
            elif command == "state":
                self._print_game_state()
                
            elif command == "bail":
                response = await self.send_and_receive(MessageType.PAY_BAIL.value)
                if response.get("type") == MessageType.GAME_STATE.value:
                    print("✓ Paid bail")
                    self._print_game_state()
                else:
                    print(f"✗ Failed: {response}")
                    
            else:
                print(f"Unknown command: {command}")
                
        except asyncio.TimeoutError:
            print("✗ Request timed out")
        except Exception as e:
            print(f"✗ Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Monopoly Terminal Test Client")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--name", default=None, help="Player name")
    args = parser.parse_args()
    
    # Get player name
    player_name = args.name
    if not player_name:
        player_name = input("Enter your name: ").strip() or "Player"
    
    client = TerminalClient(args.host, args.port, player_name)
    
    if await client.connect():
        await client.run_interactive()
    else:
        print("Failed to connect to server")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
