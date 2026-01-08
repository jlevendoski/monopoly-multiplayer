#!/usr/bin/env python3
"""
Automated test script simulating two players.
Tests the full flow: connect, create game, join, start, play a few turns.
"""

import asyncio
import json
import os
import sys
import uuid

import websockets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.enums import MessageType
from shared.constants import BOARD_SPACES


class TestPlayer:
    """A test player that can connect and play."""
    
    def __init__(self, name: str, host: str = "localhost", port: int = 8765):
        self.name = name
        self.player_id = str(uuid.uuid4())
        self.host = host
        self.port = port
        self.ws = None
        self.game_id = None
        self.game_state = None
    
    async def connect(self):
        """Connect to server."""
        url = f"ws://{self.host}:{self.port}"
        self.ws = await websockets.connect(url)
        
        # Send connect message
        await self.ws.send(json.dumps({
            "type": MessageType.CONNECT.value,
            "data": {"player_id": self.player_id, "player_name": self.name}
        }))
        
        response = await self.ws.recv()
        data = json.loads(response)
        
        if data.get("data", {}).get("success"):
            print(f"[{self.name}] ✓ Connected (ID: {self.player_id[:8]}...)")
            return True
        print(f"[{self.name}] ✗ Connect failed: {data}")
        return False
    
    async def send(self, msg_type: str, data: dict = None) -> dict:
        """Send message and get response."""
        request_id = str(uuid.uuid4())
        await self.ws.send(json.dumps({
            "type": msg_type,
            "request_id": request_id,
            "data": data or {}
        }))
        
        # Read responses until we get ours or a game state
        while True:
            response = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
            resp = json.loads(response)
            
            if resp.get("type") == MessageType.GAME_STATE.value:
                self.game_state = resp.get("data")
                self.game_id = self.game_state.get("game_id")
                return resp
            
            if resp.get("request_id") == request_id:
                return resp
            
            # Print other messages
            print(f"[{self.name}] → {resp.get('type')}: {str(resp.get('data', {}))[:100]}")
    
    async def drain_messages(self, timeout: float = 0.5):
        """Read any pending messages."""
        try:
            while True:
                msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
                data = json.loads(msg)
                if data.get("type") == MessageType.GAME_STATE.value:
                    self.game_state = data.get("data")
                    self.game_id = self.game_state.get("game_id")
                print(f"[{self.name}] → {data.get('type')}")
        except asyncio.TimeoutError:
            pass
    
    def print_state(self, verbose=False):
        """Print current game state."""
        if not self.game_state:
            print(f"[{self.name}] No game state")
            return
        
        if verbose:
            print(f"[{self.name}] RAW STATE: {json.dumps(self.game_state, indent=2)[:1500]}")
            return
        
        status = self.game_state.get('status')
        players = self.game_state.get('players', [])
        current_idx = self.game_state.get('current_player_index', 0)
        
        print(f"\n[{self.name}] Game State - {status}")
        print("-" * 50)
        for i, p in enumerate(players):
            marker = "→ " if i == current_idx else "  "
            pos = p.get('position', 0)
            space = BOARD_SPACES.get(pos, {}).get('name', f'Pos {pos}')
            jail = " [JAIL]" if p.get('is_in_jail') else ""
            print(f"  {marker}{p.get('name')}: ${p.get('money')} @ {space}{jail}")
        
        phase = self.game_state.get('phase', 'unknown')
        dice = self.game_state.get('last_dice_roll', [])
        print(f"  Phase: {phase} | Last roll: {dice}")
        print("-" * 50)
    
    async def close(self):
        if self.ws:
            await self.ws.close()


async def run_test():
    """Run a full test with two players."""
    
    print("=" * 60)
    print("MONOPOLY TWO-PLAYER TEST")
    print("=" * 60)
    
    # Create players
    player1 = TestPlayer("Alice")
    player2 = TestPlayer("Bob")
    
    try:
        # Step 1: Both players connect
        print("\n[STEP 1] Connecting players...")
        assert await player1.connect(), "Player 1 failed to connect"
        assert await player2.connect(), "Player 2 failed to connect"
        
        # Step 2: Player 1 creates a game
        print("\n[STEP 2] Player 1 creates a game...")
        resp = await player1.send(MessageType.CREATE_GAME.value, {
            "game_name": "Test Game",
            "player_name": player1.name
        })
        assert resp.get("type") == MessageType.GAME_STATE.value, f"Failed to create game: {resp}"
        game_id = player1.game_id
        print(f"[Alice] ✓ Created game: {game_id}")
        
        # Step 3: Player 2 lists games and joins
        print("\n[STEP 3] Player 2 lists and joins the game...")
        resp = await player2.send(MessageType.LIST_GAMES.value)
        games = resp.get("data", {}).get("games", [])
        print(f"[Bob] Found {len(games)} game(s)")
        
        resp = await player2.send(MessageType.JOIN_GAME.value, {
            "game_id": game_id,
            "player_name": player2.name
        })
        assert resp.get("type") == MessageType.GAME_STATE.value, f"Failed to join: {resp}"
        print(f"[Bob] ✓ Joined game")
        
        # Drain any broadcast messages
        await player1.drain_messages()
        
        # Step 4: Player 1 starts the game
        print("\n[STEP 4] Player 1 starts the game...")
        resp = await player1.send(MessageType.START_GAME.value)
        assert resp.get("type") == MessageType.GAME_STATE.value, f"Failed to start: {resp}"
        print(f"[Alice] ✓ Game started!")
        
        await player2.drain_messages()
        
        player1.print_state()
        
        # Step 5: Play a few turns
        print("\n[STEP 5] Playing some turns...")
        
        for turn_num in range(1, 5):
            print(f"\n--- Turn {turn_num} ---")
            
            # Sync both player states
            await player1.drain_messages()
            await player2.drain_messages()
            
            # Determine whose turn it is using current_player_id from state
            current_player_id = player1.game_state.get('current_player_id')
            
            if current_player_id == player1.player_id:
                current = player1
                other = player2
            elif current_player_id == player2.player_id:
                current = player2
                other = player1
            else:
                # Fallback to index-based lookup
                current_idx = player1.game_state.get('current_player_index', 0)
                players_list = player1.game_state.get('players', [])
                current_player_id = players_list[current_idx].get('id') if players_list else None
                
                if current_player_id == player1.player_id:
                    current = player1
                    other = player2
                else:
                    current = player2
                    other = player1
            
            print(f"[{current.name}'s turn]")
            
            # Roll dice
            resp = await current.send(MessageType.ROLL_DICE.value)
            if resp.get("type") == MessageType.ERROR.value:
                print(f"[{current.name}] ✗ Roll failed: {resp.get('data', {}).get('message')}")
                break
            
            # Get updated state after roll
            dice = current.game_state.get('last_dice_roll', [])
            phase = current.game_state.get('phase', 'unknown')
            
            pos = None
            for p in current.game_state.get('players', []):
                if p.get('id') == current.player_id:
                    pos = p.get('position')
                    break
            
            space = BOARD_SPACES.get(pos, {})
            print(f"[{current.name}] Rolled {dice} (sum: {sum(dice) if dice else 0}) → landed on {space.get('name', pos)} (pos {pos})")
            print(f"[{current.name}] Phase: {phase}")
            
            # Handle PROPERTY_DECISION phase - need to buy or decline
            if phase == "PROPERTY_DECISION":
                cost = space.get('cost', 0)
                print(f"[{current.name}] Must decide on property (${cost})...")
                
                # Find current player's money
                player_money = 0
                for p in current.game_state.get('players', []):
                    if p.get('id') == current.player_id:
                        player_money = p.get('money', 0)
                        break
                
                if player_money >= cost:
                    resp = await current.send(MessageType.BUY_PROPERTY.value)
                    if resp.get("type") == MessageType.ERROR.value:
                        print(f"[{current.name}] ✗ Buy failed: {resp.get('data', {}).get('message')}")
                    else:
                        print(f"[{current.name}] ✓ Bought {space.get('name')} for ${cost}!")
                else:
                    resp = await current.send(MessageType.DECLINE_PROPERTY.value)
                    print(f"[{current.name}] Declined (only has ${player_money})")
            
            # End turn
            resp = await current.send(MessageType.END_TURN.value)
            if resp.get("type") == MessageType.ERROR.value:
                error_msg = resp.get('data', {}).get('message', 'Unknown error')
                print(f"[{current.name}] ✗ End turn failed: {error_msg}")
                # If we get doubles, we might need to roll again
                if "doubles" in error_msg.lower() or "roll again" in error_msg.lower():
                    print(f"[{current.name}] (Rolled doubles, need to roll again)")
                    continue
            else:
                print(f"[{current.name}] ✓ Turn ended")
            
            # Other player drains their messages
            await other.drain_messages()
            
            # Show state
            current.print_state()
        
        print("\n" + "=" * 60)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Final state
        print("\nFinal State:")
        player1.print_state()
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await player1.close()
        await player2.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
