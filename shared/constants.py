"""
Game constants for Monopoly.
All monetary values are in Monopoly dollars.
"""

# Board spaces
BOARD_SIZE = 40
STARTING_MONEY = 1500
SALARY_AMOUNT = 200  # Passing GO

# Jail
JAIL_POSITION = 10
GO_TO_JAIL_POSITION = 30
MAX_JAIL_TURNS = 3
JAIL_BAIL = 50

# Houses and Hotels
MAX_HOUSES_PER_PROPERTY = 4
HOTEL_EQUIVALENT_HOUSES = 5
TOTAL_HOUSES = 32
TOTAL_HOTELS = 12

# Property groups (colors) with their counts
PROPERTY_GROUPS = {
    "BROWN": 2,
    "LIGHT_BLUE": 3,
    "PINK": 3,
    "ORANGE": 3,
    "RED": 3,
    "YELLOW": 3,
    "GREEN": 3,
    "DARK_BLUE": 2,
}

# Railroads and Utilities
NUM_RAILROADS = 4
NUM_UTILITIES = 2

# Cards
CHANCE_CARDS = 16
COMMUNITY_CHEST_CARDS = 16

# Property data structure
# Format: (position, name, type, cost, group, rents, house_cost)
# Rents are: [base, 1house, 2houses, 3houses, 4houses, hotel]
PROPERTIES = [
    # Special spaces
    (0, "GO", "GO", None, None, None, None),
    (10, "Jail/Just Visiting", "JAIL", None, None, None, None),
    (20, "Free Parking", "FREE_PARKING", None, None, None, None),
    (30, "Go To Jail", "GO_TO_JAIL", None, None, None, None),
    
    # Brown properties
    (1, "Mediterranean Avenue", "PROPERTY", 60, "BROWN", [2, 10, 30, 90, 160, 250], 50),
    (3, "Baltic Avenue", "PROPERTY", 60, "BROWN", [4, 20, 60, 180, 320, 450], 50),
    
    # Light Blue properties
    (6, "Oriental Avenue", "PROPERTY", 100, "LIGHT_BLUE", [6, 30, 90, 270, 400, 550], 50),
    (8, "Vermont Avenue", "PROPERTY", 100, "LIGHT_BLUE", [6, 30, 90, 270, 400, 550], 50),
    (9, "Connecticut Avenue", "PROPERTY", 120, "LIGHT_BLUE", [8, 40, 100, 300, 450, 600], 50),
    
    # Pink properties
    (11, "St. Charles Place", "PROPERTY", 140, "PINK", [10, 50, 150, 450, 625, 750], 100),
    (13, "States Avenue", "PROPERTY", 140, "PINK", [10, 50, 150, 450, 625, 750], 100),
    (14, "Virginia Avenue", "PROPERTY", 160, "PINK", [12, 60, 180, 500, 700, 900], 100),
    
    # Orange properties
    (16, "St. James Place", "PROPERTY", 180, "ORANGE", [14, 70, 200, 550, 750, 950], 100),
    (18, "Tennessee Avenue", "PROPERTY", 180, "ORANGE", [14, 70, 200, 550, 750, 950], 100),
    (19, "New York Avenue", "PROPERTY", 200, "ORANGE", [16, 80, 220, 600, 800, 1000], 100),
    
    # Red properties
    (21, "Kentucky Avenue", "PROPERTY", 220, "RED", [18, 90, 250, 700, 875, 1050], 150),
    (23, "Indiana Avenue", "PROPERTY", 220, "RED", [18, 90, 250, 700, 875, 1050], 150),
    (24, "Illinois Avenue", "PROPERTY", 240, "RED", [20, 100, 300, 750, 925, 1100], 150),
    
    # Yellow properties
    (26, "Atlantic Avenue", "PROPERTY", 260, "YELLOW", [22, 110, 330, 800, 975, 1150], 150),
    (27, "Ventnor Avenue", "PROPERTY", 260, "YELLOW", [22, 110, 330, 800, 975, 1150], 150),
    (29, "Marvin Gardens", "PROPERTY", 280, "YELLOW", [24, 120, 360, 850, 1025, 1200], 150),
    
    # Green properties
    (31, "Pacific Avenue", "PROPERTY", 300, "GREEN", [26, 130, 390, 900, 1100, 1275], 200),
    (32, "North Carolina Avenue", "PROPERTY", 300, "GREEN", [26, 130, 390, 900, 1100, 1275], 200),
    (34, "Pennsylvania Avenue", "PROPERTY", 320, "GREEN", [28, 150, 450, 1000, 1200, 1400], 200),
    
    # Dark Blue properties
    (37, "Park Place", "PROPERTY", 350, "DARK_BLUE", [35, 175, 500, 1100, 1300, 1500], 200),
    (39, "Boardwalk", "PROPERTY", 400, "DARK_BLUE", [50, 200, 600, 1400, 1700, 2000], 200),
    
    # Railroads
    (5, "Reading Railroad", "RAILROAD", 200, "RAILROAD", [25, 50, 100, 200], None),
    (15, "Pennsylvania Railroad", "RAILROAD", 200, "RAILROAD", [25, 50, 100, 200], None),
    (25, "B & O Railroad", "RAILROAD", 200, "RAILROAD", [25, 50, 100, 200], None),
    (35, "Short Line", "RAILROAD", 200, "RAILROAD", [25, 50, 100, 200], None),
    
    # Utilities
    (12, "Electric Company", "UTILITY", 150, "UTILITY", None, None),
    (28, "Water Works", "UTILITY", 150, "UTILITY", None, None),
    
    # Tax spaces
    (4, "Income Tax", "TAX", 200, None, None, None),
    (38, "Luxury Tax", "TAX", 100, None, None, None),
    
    # Card spaces
    (2, "Community Chest", "COMMUNITY_CHEST", None, None, None, None),
    (17, "Community Chest", "COMMUNITY_CHEST", None, None, None, None),
    (33, "Community Chest", "COMMUNITY_CHEST", None, None, None, None),
    (7, "Chance", "CHANCE", None, None, None, None),
    (22, "Chance", "CHANCE", None, None, None, None),
    (36, "Chance", "CHANCE", None, None, None, None),
]

# Create lookup dictionaries for easy access
BOARD_SPACES = {pos: {
    "name": name,
    "type": space_type,
    "cost": cost,
    "group": group,
    "rents": rents,
    "house_cost": house_cost
} for pos, name, space_type, cost, group, rents, house_cost in PROPERTIES}

# Utility rent multipliers
UTILITY_MULTIPLIERS = {
    1: 4,   # One utility owned: 4x dice
    2: 10   # Both utilities owned: 10x dice
}
