"""
Dice rolling mechanics.
"""
import random
from dataclasses import dataclass
from typing import Tuple


@dataclass
class DiceResult:
    """Result of rolling two dice."""
    die1: int
    die2: int
    
    @property
    def total(self) -> int:
        """Sum of both dice."""
        return self.die1 + self.die2
    
    @property
    def is_double(self) -> bool:
        """Check if both dice show the same value."""
        return self.die1 == self.die2
    
    def to_list(self) -> list[int]:
        """Return dice as a list."""
        return [self.die1, self.die2]


class Dice:
    """Handles all dice rolling for the game."""
    
    def __init__(self, seed: int | None = None):
        """
        Initialize dice roller.
        
        Args:
            seed: Optional seed for reproducible rolls (useful for testing)
        """
        self._random = random.Random(seed)
    
    def roll(self) -> DiceResult:
        """
        Roll two six-sided dice.
        
        Returns:
            DiceResult with values of both dice
        """
        die1 = self._random.randint(1, 6)
        die2 = self._random.randint(1, 6)
        return DiceResult(die1=die1, die2=die2)
    
    def set_seed(self, seed: int) -> None:
        """Set random seed for reproducible results."""
        self._random.seed(seed)
