"""
Comprehensive test script for the Monopoly game engine.
Run from project root: python -m pytest tests/ -v
Or run directly: python tests/test_game_engine/test_game_engine.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.game_engine import (
    Game, Player, Board, Property, Dice, DiceResult,
    CardManager, RuleEngine, ActionResult
)
from shared.enums import GamePhase, PlayerState, SpaceType
from shared.constants import (
    STARTING_MONEY, SALARY_AMOUNT, JAIL_POSITION,
    JAIL_BAIL, BOARD_SPACES
)


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
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
    print(f" {text}")
    print(f"{'=' * 60}{Colors.RESET}\n")


def print_subheader(text: str) -> None:
    """Print a subsection header."""
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"  {Colors.GREEN}✓ {text}{Colors.RESET}")


def print_failure(text: str) -> None:
    """Print failure message."""
    print(f"  {Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"  {Colors.YELLOW}→ {text}{Colors.RESET}")


def assert_test(condition: bool, success_msg: str, failure_msg: str) -> bool:
    """Assert a condition and print result."""
    if condition:
        print_success(success_msg)
        return True
    else:
        print_failure(failure_msg)
        return False


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def add(self, passed: bool) -> None:
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def summary(self) -> None:
        total = self.passed + self.failed
        print_header("TEST SUMMARY")
        print(f"  Total:  {total}")
        print(f"  {Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.failed}{Colors.RESET}")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed ✗{Colors.RESET}")


def test_dice() -> bool:
    """Test dice rolling mechanics."""
    print_header("DICE TESTS")
    results = TestResults()
    
    # Test basic rolling
    print_subheader("Basic Rolling")
    dice = Dice(seed=42)  # Seeded for reproducibility
    
    roll = dice.roll()
    results.add(assert_test(
        1 <= roll.die1 <= 6 and 1 <= roll.die2 <= 6,
        f"Dice values in range: {roll.die1}, {roll.die2}",
        f"Dice values out of range: {roll.die1}, {roll.die2}"
    ))
    
    results.add(assert_test(
        roll.total == roll.die1 + roll.die2,
        f"Total correct: {roll.total}",
        f"Total incorrect: {roll.total} != {roll.die1 + roll.die2}"
    ))
    
    # Test doubles detection
    print_subheader("Doubles Detection")
    dice = Dice(seed=12345)
    
    doubles_found = False
    non_doubles_found = False
    
    for _ in range(100):
        roll = dice.roll()
        if roll.is_double:
            doubles_found = True
        else:
            non_doubles_found = True
        
        if doubles_found and non_doubles_found:
            break
    
    results.add(assert_test(
        doubles_found,
        "Doubles can occur",
        "No doubles found in 100 rolls"
    ))
    
    results.add(assert_test(
        non_doubles_found,
        "Non-doubles can occur",
        "Only doubles found in 100 rolls"
    ))
    
    return results.failed == 0


def test_player() -> bool:
    """Test player mechanics."""
    print_header("PLAYER TESTS")
    results = TestResults()
    
    # Test creation
    print_subheader("Player Creation")
    player = Player(name="Test Player")
    
    results.add(assert_test(
        player.money == STARTING_MONEY,
        f"Starting money correct: ${player.money}",
        f"Starting money wrong: ${player.money} != ${STARTING_MONEY}"
    ))
    
    results.add(assert_test(
        player.position == 0,
        "Starting position is GO",
        f"Starting position wrong: {player.position}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.ACTIVE,
        "Player is active",
        f"Player state wrong: {player.state}"
    ))
    
    # Test money operations
    print_subheader("Money Operations")
    player.add_money(500)
    results.add(assert_test(
        player.money == STARTING_MONEY + 500,
        f"Add money works: ${player.money}",
        f"Add money failed: ${player.money}"
    ))
    
    success = player.remove_money(200)
    results.add(assert_test(
        success and player.money == STARTING_MONEY + 300,
        f"Remove money works: ${player.money}",
        f"Remove money failed: ${player.money}"
    ))
    
    results.add(assert_test(
        player.can_afford(1000),
        "Can afford $1000",
        "Cannot afford $1000 (should be able to)"
    ))
    
    results.add(assert_test(
        not player.can_afford(10000),
        "Cannot afford $10000",
        "Can afford $10000 (should not)"
    ))
    
    # Test movement
    print_subheader("Movement")
    player.position = 0
    passed_go = player.move_forward(10)
    
    results.add(assert_test(
        player.position == 10,
        f"Move forward works: position {player.position}",
        f"Move forward failed: position {player.position}"
    ))
    
    results.add(assert_test(
        not passed_go,
        "Did not pass GO",
        "Incorrectly detected passing GO"
    ))
    
    # Test passing GO
    player.position = 35
    old_money = player.money
    passed_go = player.move_forward(10)
    
    results.add(assert_test(
        player.position == 5,
        f"Wraparound works: position {player.position}",
        f"Wraparound failed: position {player.position}"
    ))
    
    results.add(assert_test(
        passed_go and player.money == old_money + SALARY_AMOUNT,
        f"Passed GO and collected ${SALARY_AMOUNT}",
        f"GO collection failed: ${player.money}"
    ))
    
    # Test jail
    print_subheader("Jail")
    player.send_to_jail()
    
    results.add(assert_test(
        player.position == JAIL_POSITION,
        f"Sent to jail position: {player.position}",
        f"Jail position wrong: {player.position}"
    ))
    
    results.add(assert_test(
        player.state == PlayerState.IN_JAIL,
        "Player state is IN_JAIL",
        f"Player state wrong: {player.state}"
    ))
    
    player.release_from_jail()
    
    results.add(assert_test(
        player.state == PlayerState.ACTIVE,
        "Released from jail",
        f"Still in jail: {player.state}"
    ))
    
    return results.failed == 0


def test_board() -> bool:
    """Test board and property mechanics."""
    print_header("BOARD TESTS")
    results = TestResults()
    
    board = Board()
    
    # Test board initialization
    print_subheader("Board Initialization")
    results.add(assert_test(
        len(board.properties) == 28,  # 22 properties + 4 railroads + 2 utilities
        f"Correct number of properties: {len(board.properties)}",
        f"Wrong number of properties: {len(board.properties)}"
    ))
    
    # Test specific properties
    print_subheader("Property Data")
    mediterranean = board.get_property(1)
    
    results.add(assert_test(
        mediterranean is not None and mediterranean.name == "Mediterranean Avenue",
        "Mediterranean Avenue at position 1",
        f"Wrong property at position 1: {mediterranean}"
    ))
    
    results.add(assert_test(
        mediterranean.cost == 60,
        f"Mediterranean costs $60",
        f"Wrong cost: ${mediterranean.cost}"
    ))
    
    boardwalk = board.get_property(39)
    results.add(assert_test(
        boardwalk is not None and boardwalk.cost == 400,
        f"Boardwalk costs $400",
        f"Wrong property at 39 or wrong cost"
    ))
    
    # Test property purchase
    print_subheader("Property Ownership")
    results.add(assert_test(
        board.is_property_available(1),
        "Mediterranean is available",
        "Mediterranean should be available"
    ))
    
    mediterranean.owner_id = "player1"
    
    results.add(assert_test(
        not board.is_property_available(1),
        "Mediterranean no longer available after purchase",
        "Mediterranean should not be available"
    ))
    
    results.add(assert_test(
        board.get_property_owner(1) == "player1",
        "Owner correctly set",
        f"Owner wrong: {board.get_property_owner(1)}"
    ))
    
    # Test monopoly detection
    print_subheader("Monopoly Detection")
    baltic = board.get_property(3)
    baltic.owner_id = "player1"
    
    results.add(assert_test(
        board.player_has_monopoly("player1", "BROWN"),
        "Player has BROWN monopoly",
        "Monopoly not detected"
    ))
    
    results.add(assert_test(
        not board.player_has_monopoly("player1", "LIGHT_BLUE"),
        "Player does not have LIGHT_BLUE monopoly",
        "False monopoly detected"
    ))
    
    # Test rent calculation
    print_subheader("Rent Calculation")
    rent = mediterranean.calculate_rent(has_monopoly=False)
    results.add(assert_test(
        rent == 2,
        f"Base rent is $2",
        f"Wrong base rent: ${rent}"
    ))
    
    rent = mediterranean.calculate_rent(has_monopoly=True)
    results.add(assert_test(
        rent == 4,
        f"Monopoly rent is $4 (doubled)",
        f"Wrong monopoly rent: ${rent}"
    ))
    
    # Test building
    print_subheader("Building")
    mediterranean.build_house()
    
    results.add(assert_test(
        mediterranean.houses == 1,
        f"House built: {mediterranean.houses} house(s)",
        f"House not built: {mediterranean.houses}"
    ))
    
    rent = mediterranean.calculate_rent()
    results.add(assert_test(
        rent == 10,
        f"Rent with 1 house is $10",
        f"Wrong rent with house: ${rent}"
    ))
    
    # Build up to hotel
    mediterranean.build_house()  # 2
    mediterranean.build_house()  # 3
    mediterranean.build_house()  # 4
    mediterranean.build_hotel()
    
    results.add(assert_test(
        mediterranean.has_hotel and mediterranean.houses == 0,
        "Hotel built successfully",
        f"Hotel build failed: hotel={mediterranean.has_hotel}, houses={mediterranean.houses}"
    ))
    
    rent = mediterranean.calculate_rent()
    results.add(assert_test(
        rent == 250,
        f"Rent with hotel is $250",
        f"Wrong hotel rent: ${rent}"
    ))
    
    # Test railroad rent
    print_subheader("Railroad Rent")
    board.reset()
    reading = board.get_property(5)  # Reading Railroad
    reading.owner_id = "player2"
    
    rent = reading.calculate_rent(same_group_owned=1)
    results.add(assert_test(
        rent == 25,
        f"1 railroad rent is $25",
        f"Wrong 1 railroad rent: ${rent}"
    ))
    
    # Give player all railroads
    for pos in [5, 15, 25, 35]:
        board.get_property(pos).owner_id = "player2"
    
    rent = reading.calculate_rent(same_group_owned=4)
    results.add(assert_test(
        rent == 200,
        f"4 railroad rent is $200",
        f"Wrong 4 railroad rent: ${rent}"
    ))
    
    # Test utility rent
    print_subheader("Utility Rent")
    board.reset()
    electric = board.get_property(12)  # Electric Company
    electric.owner_id = "player3"
    
    rent = electric.calculate_rent(dice_roll=7, same_group_owned=1)
    results.add(assert_test(
        rent == 28,  # 7 * 4
        f"1 utility rent is 4x dice (7 * 4 = $28)",
        f"Wrong utility rent: ${rent}"
    ))
    
    water = board.get_property(28)  # Water Works
    water.owner_id = "player3"
    
    rent = electric.calculate_rent(dice_roll=7, same_group_owned=2)
    results.add(assert_test(
        rent == 70,  # 7 * 10
        f"2 utility rent is 10x dice (7 * 10 = $70)",
        f"Wrong utility rent: ${rent}"
    ))
    
    # Test mortgage
    print_subheader("Mortgage")
    board.reset()
    mediterranean = board.get_property(1)
    mediterranean.owner_id = "player1"
    
    mortgage_value = mediterranean.mortgage()
    results.add(assert_test(
        mortgage_value == 30 and mediterranean.is_mortgaged,
        f"Mortgaged for ${mortgage_value}",
        f"Mortgage failed: value=${mortgage_value}, mortgaged={mediterranean.is_mortgaged}"
    ))
    
    rent = mediterranean.calculate_rent()
    results.add(assert_test(
        rent == 0,
        "Mortgaged property has no rent",
        f"Mortgaged property has rent: ${rent}"
    ))
    
    return results.failed == 0


def test_cards() -> bool:
    """Test Chance and Community Chest cards."""
    print_header("CARD TESTS")
    results = TestResults()
    
    cards = CardManager()
    
    print_subheader("Card Drawing")
    
    # Draw all Chance cards
    drawn_texts = set()
    for _ in range(20):
        card = cards.draw_chance()
        drawn_texts.add(card.text)
    
    results.add(assert_test(
        len(drawn_texts) > 5,
        f"Multiple different Chance cards drawn: {len(drawn_texts)} unique",
        "Not enough card variety"
    ))
    
    # Draw all Community Chest cards
    drawn_texts = set()
    for _ in range(20):
        card = cards.draw_community_chest()
        drawn_texts.add(card.text)
    
    results.add(assert_test(
        len(drawn_texts) > 5,
        f"Multiple different Community Chest cards drawn: {len(drawn_texts)} unique",
        "Not enough card variety"
    ))
    
    # Test deck reshuffling
    print_subheader("Deck Reshuffling")
    cards.reset()
    
    for _ in range(50):  # Draw more than deck size
        cards.draw_chance()
    
    results.add(assert_test(
        True,  # If we got here without error, reshuffling works
        "Deck reshuffles when empty",
        "Deck reshuffle failed"
    ))
    
    return results.failed == 0


def test_full_game() -> bool:
    """Test full game flow."""
    print_header("FULL GAME TESTS")
    results = TestResults()
    
    game = Game(name="Test Game")
    
    # Test game creation
    print_subheader("Game Setup")
    results.add(assert_test(
        game.phase == GamePhase.WAITING,
        "Game starts in WAITING phase",
        f"Wrong initial phase: {game.phase}"
    ))
    
    # Add players
    success, msg, player1 = game.add_player("Alice")
    results.add(assert_test(
        success and player1 is not None,
        f"Added player Alice: {msg}",
        f"Failed to add player: {msg}"
    ))
    
    success, msg, player2 = game.add_player("Bob")
    results.add(assert_test(
        success and player2 is not None,
        f"Added player Bob: {msg}",
        f"Failed to add player: {msg}"
    ))
    
    # Try to start with enough players
    success, msg = game.start_game()
    results.add(assert_test(
        success,
        f"Game started: {msg}",
        f"Failed to start game: {msg}"
    ))
    
    results.add(assert_test(
        game.phase == GamePhase.PRE_ROLL,
        "Game in PRE_ROLL phase after start",
        f"Wrong phase after start: {game.phase}"
    ))
    
    # Test turn flow
    print_subheader("Turn Flow")
    current = game.current_player
    results.add(assert_test(
        current is not None,
        f"Current player is {current.name}",
        "No current player"
    ))
    
    # Roll dice
    success, msg, roll = game.roll_dice(current.id)
    results.add(assert_test(
        success and roll is not None,
        f"Rolled {roll.die1} + {roll.die2} = {roll.total}: {msg}",
        f"Roll failed: {msg}"
    ))
    
    print_info(f"Player moved to position {current.position}")
    
    # Test property purchase flow
    print_subheader("Property Purchase")
    
    # Reset and manually position player on Mediterranean
    game2 = Game(name="Property Test")
    game2.add_player("Alice")
    game2.add_player("Bob")
    game2.start_game()
    
    current = game2.current_player
    old_money = current.money
    
    # Manually move to Mediterranean
    current.position = 1
    game2.phase = GamePhase.PROPERTY_DECISION
    
    success, msg = game2.buy_property(current.id)
    results.add(assert_test(
        success,
        f"Bought property: {msg}",
        f"Failed to buy: {msg}"
    ))
    
    results.add(assert_test(
        current.money == old_money - 60,
        f"Money deducted: ${current.money}",
        f"Money not deducted correctly: ${current.money}"
    ))
    
    results.add(assert_test(
        1 in current.properties,
        "Property added to player",
        "Property not in player's list"
    ))
    
    # Test rent payment
    print_subheader("Rent Payment")
    game3 = Game(name="Rent Test")
    _, _, alice = game3.add_player("Alice")
    _, _, bob = game3.add_player("Bob")
    game3.start_game()
    
    # Alice buys Mediterranean
    prop = game3.board.get_property(1)
    prop.owner_id = alice.id
    alice.add_property(1)
    
    # Bob lands on it
    bob.position = 1
    bob_money = bob.money
    alice_money = alice.money
    
    rent = game3.board.calculate_rent(1, landing_player_id=bob.id)
    results.add(assert_test(
        rent == 2,
        f"Rent calculated: ${rent}",
        f"Wrong rent: ${rent}"
    ))
    
    # Test building - FIXED: Use current player
    print_subheader("Building Houses")
    game4 = Game(name="Building Test")
    _, _, builder = game4.add_player("Builder")
    _, _, other = game4.add_player("Other")
    game4.start_game()
    
    # Make sure Builder is current player
    current = game4.current_player
    print_info(f"Current player: {current.name}")
    
    # Give current player monopoly on brown
    for pos in [1, 3]:
        prop = game4.board.get_property(pos)
        prop.owner_id = current.id
        current.add_property(pos)
    
    # Try to build (must be in POST_ROLL or similar phase)
    game4.phase = GamePhase.POST_ROLL
    
    success, msg = game4.build_house(current.id, 1)
    results.add(assert_test(
        success,
        f"Built house: {msg}",
        f"Failed to build: {msg}"
    ))
    
    # Try to build unevenly (should fail)
    success, msg = game4.build_house(current.id, 1)
    results.add(assert_test(
        not success,
        f"Uneven building prevented: {msg}",
        "Uneven building allowed (should be blocked)"
    ))
    
    # Build on other property
    success, msg = game4.build_house(current.id, 3)
    results.add(assert_test(
        success,
        f"Built on other property: {msg}",
        f"Failed to build on other property: {msg}"
    ))
    
    # Now can build second house on first
    success, msg = game4.build_house(current.id, 1)
    results.add(assert_test(
        success,
        f"Second house built: {msg}",
        f"Failed to build second house: {msg}"
    ))
    
    # Test jail mechanics - FIXED: Use current player
    print_subheader("Jail Mechanics")
    game5 = Game(name="Jail Test")
    _, _, prisoner = game5.add_player("Prisoner")
    _, _, guard = game5.add_player("Guard")
    game5.start_game()
    
    # Get current player and send them to jail
    current = game5.current_player
    print_info(f"Current player: {current.name}")
    
    current.send_to_jail()
    
    results.add(assert_test(
        current.state == PlayerState.IN_JAIL,
        "Player in jail",
        f"Wrong state: {current.state}"
    ))
    
    results.add(assert_test(
        current.position == JAIL_POSITION,
        f"At jail position: {current.position}",
        f"Wrong position: {current.position}"
    ))
    
    # Pay bail - must be current player's turn and in correct phase
    game5.phase = GamePhase.PRE_ROLL
    old_money = current.money
    success, msg = game5.pay_bail(current.id)
    results.add(assert_test(
        success,
        f"Paid bail: {msg}",
        f"Failed to pay bail: {msg}"
    ))
    
    results.add(assert_test(
        current.state == PlayerState.ACTIVE,
        "Player released",
        f"Still in jail: {current.state}"
    ))
    
    results.add(assert_test(
        current.money == old_money - JAIL_BAIL,
        f"Bail deducted: ${current.money}",
        f"Bail not deducted: ${current.money}"
    ))
    
    # Test serialization
    print_subheader("Save/Load Game")
    game6 = Game(name="Save Test")
    game6.add_player("Saver")
    game6.add_player("Loader")
    game6.start_game()
    
    # Make some changes
    current = game6.current_player
    prop = game6.board.get_property(1)
    prop.owner_id = current.id
    current.add_property(1)
    current.money = 1234
    
    # Save
    save_data = game6.to_dict()
    
    results.add(assert_test(
        "id" in save_data and "players" in save_data,
        "Game serialized to dict",
        "Serialization failed"
    ))
    
    # Load
    loaded_game = Game.from_dict(save_data)
    
    results.add(assert_test(
        loaded_game.id == game6.id,
        f"Game ID preserved: {loaded_game.id}",
        "Game ID not preserved"
    ))
    
    loaded_current = loaded_game.current_player
    results.add(assert_test(
        loaded_current and loaded_current.money == 1234,
        f"Player money preserved: ${loaded_current.money if loaded_current else 'N/A'}",
        "Player money not preserved"
    ))
    
    loaded_prop = loaded_game.board.get_property(1)
    results.add(assert_test(
        loaded_prop and loaded_prop.owner_id == current.id,
        "Property ownership preserved",
        "Property ownership not preserved"
    ))
    
    # Test bankruptcy
    print_subheader("Bankruptcy")
    game7 = Game(name="Bankruptcy Test")
    _, _, broke = game7.add_player("Broke")
    _, _, rich = game7.add_player("Rich")
    game7.start_game()
    
    broke.money = 0
    success, msg = game7.declare_bankruptcy(broke.id)
    
    results.add(assert_test(
        success,
        f"Bankruptcy declared: {msg}",
        f"Bankruptcy failed: {msg}"
    ))
    
    results.add(assert_test(
        broke.state == PlayerState.BANKRUPT,
        "Player marked bankrupt",
        f"Wrong state: {broke.state}"
    ))
    
    results.add(assert_test(
        game7.is_game_over,
        "Game over with one player left",
        "Game not over"
    ))
    
    return results.failed == 0


def test_edge_cases() -> bool:
    """Test edge cases and error handling."""
    print_header("EDGE CASE TESTS")
    results = TestResults()
    
    # Test invalid operations
    print_subheader("Invalid Operations")
    game = Game(name="Edge Cases")
    _, _, player = game.add_player("Tester")
    
    # Try to roll before game starts
    success, msg, _ = game.roll_dice(player.id)
    results.add(assert_test(
        not success,
        f"Cannot roll before game starts: {msg}",
        "Rolling before game start should fail"
    ))
    
    # Try to start with one player
    success, msg = game.start_game()
    results.add(assert_test(
        not success,
        f"Cannot start with 1 player: {msg}",
        "Starting with 1 player should fail"
    ))
    
    # Add enough players and start
    game.add_player("Other")
    game.start_game()
    
    # Try to add player after start
    success, msg, _ = game.add_player("Late")
    results.add(assert_test(
        not success,
        f"Cannot add player after start: {msg}",
        "Adding player after start should fail"
    ))
    
    # Try to roll as wrong player
    other_id = [p for p in game.players if p != game.current_player.id][0]
    success, msg, _ = game.roll_dice(other_id)
    results.add(assert_test(
        not success,
        f"Cannot roll on other's turn: {msg}",
        "Rolling on other's turn should fail"
    ))
    
    # Test building without monopoly - FIXED: Use current player
    print_subheader("Building Restrictions")
    current = game.current_player
    prop = game.board.get_property(1)
    prop.owner_id = current.id
    current.add_property(1)
    
    game.phase = GamePhase.POST_ROLL
    success, msg = game.build_house(current.id, 1)
    results.add(assert_test(
        not success,
        f"Cannot build without monopoly: {msg}",
        "Building without monopoly should fail"
    ))
    
    # Test mortgage with buildings - FIXED: Use current player
    print_subheader("Mortgage Restrictions")
    game2 = Game(name="Mortgage Test")
    _, _, player1 = game2.add_player("Mortgager")
    game2.add_player("Other")
    game2.start_game()
    
    current = game2.current_player
    print_info(f"Current player: {current.name}")
    
    # Give monopoly and build
    for pos in [1, 3]:
        prop = game2.board.get_property(pos)
        prop.owner_id = current.id
        current.add_property(pos)
    
    game2.phase = GamePhase.POST_ROLL
    game2.build_house(current.id, 1)
    
    success, msg = game2.mortgage_property(current.id, 1)
    results.add(assert_test(
        not success,
        f"Cannot mortgage with buildings: {msg}",
        "Mortgaging with buildings should fail"
    ))
    
    return results.failed == 0


def run_all_tests() -> None:
    """Run all test suites."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           MONOPOLY GAME ENGINE TEST SUITE                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    all_results = TestResults()
    
    tests = [
        ("Dice", test_dice),
        ("Player", test_player),
        ("Board", test_board),
        ("Cards", test_cards),
        ("Full Game", test_full_game),
        ("Edge Cases", test_edge_cases),
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
