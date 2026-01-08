"""
Tests for the persistence layer.

Run with: python3 tests/test_persistence/test_persistence.py
"""

import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.persistence import (
    Database,
    init_database,
    GameRepository,
    GameRecord,
    PlayerRecord,
    PropertyRecord,
    CardDeckRecord,
)


class PersistenceTestCase(unittest.TestCase):
    """Base test case with database setup/teardown."""
    
    def setUp(self):
        """Create a temporary database for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.db = init_database(self.db_path)
        self.repository = GameRepository(self.db)
    
    def tearDown(self):
        """Clean up the temporary database."""
        self.db.close_connection()
        Path(self.db_path).unlink(missing_ok=True)
    
    def create_sample_game(self) -> GameRecord:
        """Create and save a sample game."""
        game = GameRecord(
            id=str(uuid.uuid4()),
            name="Test Game",
            status="in_progress",
            current_player_index=0,
            settings_json=json.dumps({"starting_money": 1500})
        )
        self.repository.create_game(game)
        return game
    
    def create_sample_players(self, game: GameRecord) -> list[PlayerRecord]:
        """Create and save sample players for a game."""
        players = [
            PlayerRecord(
                id=str(uuid.uuid4()),
                game_id=game.id,
                name="Alice",
                token="car",
                turn_order=0,
                position=5,
                money=1200,
                is_bankrupt=False,
                is_in_jail=False,
                jail_turns=0,
                get_out_of_jail_cards=1,
                connected=True
            ),
            PlayerRecord(
                id=str(uuid.uuid4()),
                game_id=game.id,
                name="Bob",
                token="hat",
                turn_order=1,
                position=15,
                money=1800,
                is_bankrupt=False,
                is_in_jail=True,
                jail_turns=2,
                get_out_of_jail_cards=0,
                connected=True
            )
        ]
        for player in players:
            self.repository.add_player(player)
        return players
    
    def create_sample_properties(self, game: GameRecord, players: list[PlayerRecord]) -> list[PropertyRecord]:
        """Create and save sample properties."""
        properties = [
            PropertyRecord(
                game_id=game.id,
                position=1,
                owner_id=players[0].id,
                houses=2,
                is_mortgaged=False
            ),
            PropertyRecord(
                game_id=game.id,
                position=3,
                owner_id=players[0].id,
                houses=2,
                is_mortgaged=False
            ),
            PropertyRecord(
                game_id=game.id,
                position=6,
                owner_id=players[1].id,
                houses=0,
                is_mortgaged=True
            ),
            PropertyRecord(
                game_id=game.id,
                position=39,
                owner_id=players[1].id,
                houses=1,
                is_mortgaged=False
            )
        ]
        for prop in properties:
            self.repository.save_property(prop)
        return properties
    
    def create_sample_card_decks(self, game: GameRecord) -> list[CardDeckRecord]:
        """Create and save sample card decks."""
        decks = [
            CardDeckRecord(
                game_id=game.id,
                deck_type="chance",
                card_order_json=json.dumps(list(range(16))),
                current_index=3
            ),
            CardDeckRecord(
                game_id=game.id,
                deck_type="community_chest",
                card_order_json=json.dumps(list(range(16))),
                current_index=1
            )
        ]
        for deck in decks:
            self.repository.save_card_deck(deck)
        return decks


class TestDatabase(PersistenceTestCase):
    """Test database connection and schema management."""
    
    def test_database_creation(self):
        """Test that database and tables are created."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN 
                ('games', 'players', 'properties', 'game_states', 'card_decks')
                """
            )
            tables = [row['name'] for row in cursor.fetchall()]
            
            self.assertIn('games', tables)
            self.assertIn('players', tables)
            self.assertIn('properties', tables)
            self.assertIn('game_states', tables)
            self.assertIn('card_decks', tables)
    
    def test_foreign_keys_enabled(self):
        """Test that foreign keys are enforced."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
    
    def test_reset_database(self):
        """Test database reset functionality."""
        game = self.create_sample_game()
        
        retrieved = self.repository.get_game(game.id)
        self.assertIsNotNone(retrieved)
        
        self.db.reset_database()
        
        retrieved = self.repository.get_game(game.id)
        self.assertIsNone(retrieved)


class TestGameOperations(PersistenceTestCase):
    """Test game CRUD operations."""
    
    def test_create_and_get_game(self):
        """Test creating and retrieving a game."""
        game = GameRecord(
            id=str(uuid.uuid4()),
            name="Test Game",
            status="in_progress"
        )
        
        created = self.repository.create_game(game)
        self.assertEqual(created.id, game.id)
        
        retrieved = self.repository.get_game(game.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, game.id)
        self.assertEqual(retrieved.name, game.name)
        self.assertEqual(retrieved.status, game.status)
    
    def test_get_nonexistent_game(self):
        """Test getting a game that doesn't exist."""
        retrieved = self.repository.get_game("nonexistent-id")
        self.assertIsNone(retrieved)
    
    def test_update_game(self):
        """Test updating a game."""
        game = self.create_sample_game()
        
        game.status = "finished"
        game.winner_id = "player-123"
        self.repository.update_game(game)
        
        retrieved = self.repository.get_game(game.id)
        self.assertEqual(retrieved.status, "finished")
        self.assertEqual(retrieved.winner_id, "player-123")
    
    def test_delete_game(self):
        """Test deleting a game."""
        game = self.create_sample_game()
        
        deleted = self.repository.delete_game(game.id)
        self.assertTrue(deleted)
        
        retrieved = self.repository.get_game(game.id)
        self.assertIsNone(retrieved)
    
    def test_delete_nonexistent_game(self):
        """Test deleting a game that doesn't exist."""
        deleted = self.repository.delete_game("nonexistent-id")
        self.assertFalse(deleted)
    
    def test_list_games(self):
        """Test listing games."""
        for i in range(5):
            game = GameRecord(
                id=f"game-{i}",
                name=f"Game {i}",
                status="waiting" if i < 2 else "in_progress"
            )
            self.repository.create_game(game)
        
        all_games = self.repository.list_games()
        self.assertEqual(len(all_games), 5)
    
    def test_list_games_by_status(self):
        """Test listing games filtered by status."""
        for i in range(5):
            game = GameRecord(
                id=f"game-{i}",
                name=f"Game {i}",
                status="waiting" if i < 2 else "in_progress"
            )
            self.repository.create_game(game)
        
        waiting = self.repository.list_games(status="waiting")
        self.assertEqual(len(waiting), 2)
        
        in_progress = self.repository.list_games(status="in_progress")
        self.assertEqual(len(in_progress), 3)
    
    def test_list_games_pagination(self):
        """Test listing games with pagination."""
        for i in range(5):
            game = GameRecord(
                id=f"game-{i}",
                name=f"Game {i}",
                status="waiting"
            )
            self.repository.create_game(game)
        
        first_page = self.repository.list_games(limit=2, offset=0)
        self.assertEqual(len(first_page), 2)
        
        second_page = self.repository.list_games(limit=2, offset=2)
        self.assertEqual(len(second_page), 2)
        
        third_page = self.repository.list_games(limit=2, offset=4)
        self.assertEqual(len(third_page), 1)


class TestPlayerOperations(PersistenceTestCase):
    """Test player CRUD operations."""
    
    def test_add_and_get_player(self):
        """Test adding and retrieving a player."""
        game = self.create_sample_game()
        
        player = PlayerRecord(
            id=str(uuid.uuid4()),
            game_id=game.id,
            name="Alice",
            token="car",
            turn_order=0,
            position=5,
            money=1200
        )
        self.repository.add_player(player)
        
        retrieved = self.repository.get_player(player.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Alice")
        self.assertEqual(retrieved.token, "car")
        self.assertEqual(retrieved.money, 1200)
        self.assertEqual(retrieved.position, 5)
    
    def test_get_nonexistent_player(self):
        """Test getting a player that doesn't exist."""
        retrieved = self.repository.get_player("nonexistent-id")
        self.assertIsNone(retrieved)
    
    def test_get_players_for_game(self):
        """Test retrieving all players for a game."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        
        retrieved = self.repository.get_players_for_game(game.id)
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0].turn_order, 0)
        self.assertEqual(retrieved[1].turn_order, 1)
    
    def test_get_players_for_empty_game(self):
        """Test getting players for a game with no players."""
        game = self.create_sample_game()
        
        players = self.repository.get_players_for_game(game.id)
        self.assertEqual(len(players), 0)
    
    def test_update_player(self):
        """Test updating player data."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        player = players[0]
        
        player.money = 500
        player.position = 20
        player.is_in_jail = True
        player.jail_turns = 1
        self.repository.update_player(player)
        
        retrieved = self.repository.get_player(player.id)
        self.assertEqual(retrieved.money, 500)
        self.assertEqual(retrieved.position, 20)
        self.assertTrue(retrieved.is_in_jail)
        self.assertEqual(retrieved.jail_turns, 1)
    
    def test_update_player_connection(self):
        """Test updating player connection status."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        player = players[0]
        
        self.repository.update_player_connection(player.id, False)
        retrieved = self.repository.get_player(player.id)
        self.assertFalse(retrieved.connected)
        
        self.repository.update_player_connection(player.id, True)
        retrieved = self.repository.get_player(player.id)
        self.assertTrue(retrieved.connected)


class TestPropertyOperations(PersistenceTestCase):
    """Test property CRUD operations."""
    
    def test_save_and_get_properties(self):
        """Test saving and retrieving properties."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        properties = self.create_sample_properties(game, players)
        
        retrieved = self.repository.get_properties_for_game(game.id)
        self.assertEqual(len(retrieved), 4)
        self.assertEqual(retrieved[0].position, 1)
        self.assertEqual(retrieved[0].houses, 2)
    
    def test_get_properties_for_player(self):
        """Test retrieving properties by player."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        self.create_sample_properties(game, players)
        
        alice_props = self.repository.get_properties_for_player(players[0].id)
        self.assertEqual(len(alice_props), 2)
        for prop in alice_props:
            self.assertEqual(prop.owner_id, players[0].id)
        
        bob_props = self.repository.get_properties_for_player(players[1].id)
        self.assertEqual(len(bob_props), 2)
        for prop in bob_props:
            self.assertEqual(prop.owner_id, players[1].id)
    
    def test_update_property(self):
        """Test updating property ownership and development."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        
        prop = PropertyRecord(
            game_id=game.id,
            position=1,
            owner_id=players[0].id,
            houses=2,
            is_mortgaged=False
        )
        self.repository.save_property(prop)
        
        prop.houses = 5  # Hotel
        prop.is_mortgaged = True
        self.repository.save_property(prop)
        
        properties = self.repository.get_properties_for_game(game.id)
        updated = [p for p in properties if p.position == 1][0]
        self.assertEqual(updated.houses, 5)
        self.assertTrue(updated.is_mortgaged)
    
    def test_property_ownership_change(self):
        """Test changing property ownership."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        
        prop = PropertyRecord(
            game_id=game.id,
            position=1,
            owner_id=players[0].id,
            houses=0
        )
        self.repository.save_property(prop)
        
        # Transfer to second player
        prop.owner_id = players[1].id
        self.repository.save_property(prop)
        
        alice_props = self.repository.get_properties_for_player(players[0].id)
        bob_props = self.repository.get_properties_for_player(players[1].id)
        
        self.assertEqual(len(alice_props), 0)
        self.assertEqual(len(bob_props), 1)
        self.assertEqual(bob_props[0].position, 1)


class TestGameStateSnapshots(PersistenceTestCase):
    """Test game state snapshot operations."""
    
    def test_save_and_get_snapshot(self):
        """Test saving and retrieving game state snapshots."""
        game = self.create_sample_game()
        
        game_state = {
            "turn": 10,
            "players": ["player1", "player2"],
            "dice": {"last_roll": [3, 4]}
        }
        
        snapshot_id = self.repository.save_game_state(game.id, game_state, 10)
        self.assertGreater(snapshot_id, 0)
        
        snapshot = self.repository.get_latest_game_state(game.id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.turn_number, 10)
        
        loaded_state = json.loads(snapshot.state_json)
        self.assertEqual(loaded_state["turn"], 10)
        self.assertEqual(loaded_state["dice"]["last_roll"], [3, 4])
    
    def test_get_latest_snapshot_multiple(self):
        """Test getting latest snapshot when multiple exist."""
        game = self.create_sample_game()
        
        for turn in [5, 10, 15]:
            self.repository.save_game_state(game.id, {"turn": turn}, turn)
        
        snapshot = self.repository.get_latest_game_state(game.id)
        state = json.loads(snapshot.state_json)
        self.assertEqual(state["turn"], 15)
    
    def test_get_snapshot_at_turn(self):
        """Test retrieving snapshots at specific turns."""
        game = self.create_sample_game()
        
        for turn in [5, 10, 15, 20]:
            self.repository.save_game_state(game.id, {"turn": turn}, turn)
        
        # Turn 12 should return turn 10 snapshot
        snapshot = self.repository.get_game_state_at_turn(game.id, 12)
        state = json.loads(snapshot.state_json)
        self.assertEqual(state["turn"], 10)
        
        # Turn 20 should return turn 20 snapshot
        snapshot = self.repository.get_game_state_at_turn(game.id, 20)
        state = json.loads(snapshot.state_json)
        self.assertEqual(state["turn"], 20)
        
        # Turn 3 should return None (no snapshot at or before turn 3)
        snapshot = self.repository.get_game_state_at_turn(game.id, 3)
        self.assertIsNone(snapshot)
    
    def test_get_snapshot_nonexistent_game(self):
        """Test getting snapshot for nonexistent game."""
        snapshot = self.repository.get_latest_game_state("nonexistent")
        self.assertIsNone(snapshot)
    
    def test_cleanup_old_snapshots(self):
        """Test cleaning up old snapshots."""
        game = self.create_sample_game()
        
        for turn in range(20):
            self.repository.save_game_state(game.id, {"turn": turn}, turn)
        
        deleted = self.repository.cleanup_old_snapshots(game.id, keep_count=5)
        self.assertEqual(deleted, 15)
        
        with self.repository.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM game_states WHERE game_id = ?",
                (game.id,)
            )
            count = cursor.fetchone()["count"]
            self.assertEqual(count, 5)


class TestCardDeckOperations(PersistenceTestCase):
    """Test card deck operations."""
    
    def test_save_and_get_card_decks(self):
        """Test saving and retrieving card deck states."""
        game = self.create_sample_game()
        decks = self.create_sample_card_decks(game)
        
        retrieved = self.repository.get_card_decks(game.id)
        self.assertEqual(len(retrieved), 2)
        
        chance = [d for d in retrieved if d.deck_type == "chance"][0]
        self.assertEqual(chance.current_index, 3)
        cards = json.loads(chance.card_order_json)
        self.assertEqual(len(cards), 16)
        
        community = [d for d in retrieved if d.deck_type == "community_chest"][0]
        self.assertEqual(community.current_index, 1)
    
    def test_update_card_deck(self):
        """Test updating card deck state."""
        game = self.create_sample_game()
        
        deck = CardDeckRecord(
            game_id=game.id,
            deck_type="chance",
            card_order_json=json.dumps(list(range(16))),
            current_index=0
        )
        self.repository.save_card_deck(deck)
        
        deck.current_index = 7
        deck.card_order_json = json.dumps(list(range(15, -1, -1)))
        self.repository.save_card_deck(deck)
        
        decks = self.repository.get_card_decks(game.id)
        updated = decks[0]
        self.assertEqual(updated.current_index, 7)
        cards = json.loads(updated.card_order_json)
        self.assertEqual(cards[0], 15)
        self.assertEqual(cards[-1], 0)


class TestFullGameSaveLoad(PersistenceTestCase):
    """Test complete game save/load cycles."""
    
    def test_save_full_game(self):
        """Test saving a complete game state."""
        game = GameRecord(
            id=str(uuid.uuid4()),
            name="Full Test Game",
            status="in_progress"
        )
        
        players = [
            PlayerRecord(
                id=str(uuid.uuid4()),
                game_id=game.id,
                name="Alice",
                token="car",
                turn_order=0
            ),
            PlayerRecord(
                id=str(uuid.uuid4()),
                game_id=game.id,
                name="Bob",
                token="hat",
                turn_order=1
            )
        ]
        
        properties = [
            PropertyRecord(game_id=game.id, position=1, owner_id=players[0].id),
            PropertyRecord(game_id=game.id, position=39, owner_id=players[1].id)
        ]
        
        card_decks = [
            CardDeckRecord(
                game_id=game.id,
                deck_type="chance",
                card_order_json=json.dumps(list(range(16))),
                current_index=0
            )
        ]
        
        state_snapshot = {"turn": 25, "dice": [4, 2]}
        
        self.repository.save_full_game(
            game=game,
            players=players,
            properties=properties,
            card_decks=card_decks,
            state_snapshot=state_snapshot,
            turn_number=25
        )
        
        self.assertIsNotNone(self.repository.get_game(game.id))
        self.assertEqual(len(self.repository.get_players_for_game(game.id)), 2)
        self.assertEqual(len(self.repository.get_properties_for_game(game.id)), 2)
        self.assertEqual(len(self.repository.get_card_decks(game.id)), 1)
        
        snapshot = self.repository.get_latest_game_state(game.id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.turn_number, 25)
    
    def test_load_full_game(self):
        """Test loading a complete game state."""
        game = GameRecord(
            id=str(uuid.uuid4()),
            name="Full Test Game",
            status="in_progress"
        )
        
        players = [
            PlayerRecord(
                id=str(uuid.uuid4()),
                game_id=game.id,
                name="Alice",
                token="car",
                turn_order=0
            )
        ]
        
        properties = [
            PropertyRecord(game_id=game.id, position=1, owner_id=players[0].id)
        ]
        
        card_decks = [
            CardDeckRecord(
                game_id=game.id,
                deck_type="chance",
                card_order_json=json.dumps(list(range(16))),
                current_index=0
            )
        ]
        
        self.repository.save_full_game(
            game=game,
            players=players,
            properties=properties,
            card_decks=card_decks,
            state_snapshot={"test": "data"},
            turn_number=30
        )
        
        loaded = self.repository.load_full_game(game.id)
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["game"].id, game.id)
        self.assertEqual(len(loaded["players"]), 1)
        self.assertEqual(len(loaded["properties"]), 1)
        self.assertEqual(len(loaded["card_decks"]), 1)
        self.assertEqual(loaded["latest_snapshot"].turn_number, 30)
    
    def test_load_nonexistent_game(self):
        """Test loading a game that doesn't exist."""
        loaded = self.repository.load_full_game("nonexistent-game")
        self.assertIsNone(loaded)
    
    def test_cascading_delete(self):
        """Test that deleting a game cascades to all related data."""
        game = self.create_sample_game()
        players = self.create_sample_players(game)
        self.create_sample_properties(game, players)
        self.create_sample_card_decks(game)
        self.repository.save_game_state(game.id, {"test": "data"}, 1)
        
        self.repository.delete_game(game.id)
        
        self.assertIsNone(self.repository.get_game(game.id))
        self.assertEqual(len(self.repository.get_players_for_game(game.id)), 0)
        self.assertEqual(len(self.repository.get_properties_for_game(game.id)), 0)
        self.assertEqual(len(self.repository.get_card_decks(game.id)), 0)
        self.assertIsNone(self.repository.get_latest_game_state(game.id))
    
    def test_update_existing_game(self):
        """Test that save_full_game updates existing records."""
        game = GameRecord(
            id=str(uuid.uuid4()),
            name="Original Name",
            status="waiting"
        )
        
        players = [
            PlayerRecord(
                id=str(uuid.uuid4()),
                game_id=game.id,
                name="Alice",
                token="car",
                turn_order=0,
                money=1500,
                position=0
            )
        ]
        
        # Initial save
        self.repository.save_full_game(game=game, players=players, properties=[], card_decks=[])
        
        # Update game and player
        game.name = "Updated Name"
        game.status = "in_progress"
        players[0].money = 1000
        players[0].position = 10
        
        # Save again
        self.repository.save_full_game(game=game, players=players, properties=[], card_decks=[])
        
        # Verify updates
        loaded = self.repository.load_full_game(game.id)
        self.assertEqual(loaded["game"].name, "Updated Name")
        self.assertEqual(loaded["game"].status, "in_progress")
        self.assertEqual(loaded["players"][0].money, 1000)
        self.assertEqual(loaded["players"][0].position, 10)


def run_tests():
    """Run all persistence tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDatabase,
        TestGameOperations,
        TestPlayerOperations,
        TestPropertyOperations,
        TestGameStateSnapshots,
        TestCardDeckOperations,
        TestFullGameSaveLoad,
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
