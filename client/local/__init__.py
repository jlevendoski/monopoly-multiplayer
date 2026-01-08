"""
Local (offline) game module.

Allows playing Monopoly without a server - hot-seat multiplayer on one device.
"""

from .controller import LocalGameController
from .local_main import run_local_game

__all__ = ["LocalGameController", "run_local_game"]
