"""
Monopoly client entry point.

Starts the GUI application with async support for network operations.
"""

import sys
import asyncio
import logging

from PyQt6.QtWidgets import QApplication

# Use qasync to integrate asyncio with Qt's event loop
try:
    import qasync
except ImportError:
    print("Please install qasync: pip install qasync")
    sys.exit(1)

from client.gui import MainWindow
from client.config import settings


def setup_logging() -> None:
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


async def main_async() -> None:
    """Async main function."""
    # Keep the app running
    while True:
        await asyncio.sleep(1)


def main() -> int:
    """Main entry point."""
    setup_logging()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Monopoly")
    app.setOrganizationName("Monopoly")
    
    # Set up async event loop with Qt
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the event loop
    with loop:
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
