"""
Property detail dialog.

Shows full details about a property when clicked.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from shared.constants import BOARD_SPACES
from client.gui.styles import PROPERTY_COLORS


class PropertyDialog(QDialog):
    """Dialog showing property details."""
    
    def __init__(self, position: int, game_state: dict, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Property Details")
        self.setMinimumWidth(300)
        
        space = BOARD_SPACES.get(position, {})
        prop_data = game_state.get("board", {}).get(str(position), {})
        
        layout = QVBoxLayout(self)
        
        # Color bar
        group = space.get("group")
        if group and group in PROPERTY_COLORS:
            color_bar = QFrame()
            color_bar.setFixedHeight(30)
            color = PROPERTY_COLORS[group]
            color_bar.setStyleSheet(f"background-color: {color.name()};")
            layout.addWidget(color_bar)
        
        # Name
        name = space.get("name", f"Space {position}")
        name_label = QLabel(name)
        name_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Type
        space_type = space.get("type", "")
        type_label = QLabel(space_type.replace("_", " ").title())
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(type_label)
        
        layout.addSpacing(10)
        
        # Details frame
        details = QFrame()
        details.setFrameStyle(QFrame.Shape.Box)
        details.setStyleSheet("background-color: #34495E; padding: 10px;")
        details_layout = QGridLayout(details)
        
        row = 0
        
        # Cost
        cost = space.get("cost")
        if cost:
            details_layout.addWidget(QLabel("Purchase Price:"), row, 0)
            details_layout.addWidget(QLabel(f"${cost}"), row, 1)
            row += 1
        
        # Owner
        owner_id = prop_data.get("owner_id")
        if owner_id:
            owner_name = "Unknown"
            for p in game_state.get("players", []):
                if p.get("id") == owner_id:
                    owner_name = p.get("name", "Unknown")
                    break
            details_layout.addWidget(QLabel("Owner:"), row, 0)
            details_layout.addWidget(QLabel(owner_name), row, 1)
            row += 1
        
        # Mortgage status
        if prop_data.get("is_mortgaged"):
            details_layout.addWidget(QLabel("Status:"), row, 0)
            mortgaged_label = QLabel("MORTGAGED")
            mortgaged_label.setStyleSheet("color: #E74C3C; font-weight: bold;")
            details_layout.addWidget(mortgaged_label, row, 1)
            row += 1
        
        # Buildings
        houses = prop_data.get("houses", 0)
        has_hotel = prop_data.get("has_hotel", False)
        if has_hotel:
            details_layout.addWidget(QLabel("Buildings:"), row, 0)
            details_layout.addWidget(QLabel("🏨 Hotel"), row, 1)
            row += 1
        elif houses > 0:
            details_layout.addWidget(QLabel("Buildings:"), row, 0)
            details_layout.addWidget(QLabel(f"🏠 x{houses}"), row, 1)
            row += 1
        
        # Rent table for properties
        rents = space.get("rents")
        if rents and space_type == "PROPERTY":
            details_layout.addWidget(QLabel(""), row, 0)
            row += 1
            details_layout.addWidget(QLabel("Rent:"), row, 0)
            details_layout.addWidget(QLabel(f"${rents[0]}"), row, 1)
            row += 1
            
            rent_labels = ["With 1 House:", "With 2 Houses:", "With 3 Houses:", "With 4 Houses:", "With Hotel:"]
            for i, label in enumerate(rent_labels):
                details_layout.addWidget(QLabel(label), row, 0)
                details_layout.addWidget(QLabel(f"${rents[i+1]}"), row, 1)
                row += 1
            
            # House cost
            house_cost = space.get("house_cost", 0)
            details_layout.addWidget(QLabel(""), row, 0)
            row += 1
            details_layout.addWidget(QLabel("House Cost:"), row, 0)
            details_layout.addWidget(QLabel(f"${house_cost}"), row, 1)
            row += 1
        
        elif rents and space_type == "RAILROAD":
            details_layout.addWidget(QLabel(""), row, 0)
            row += 1
            details_layout.addWidget(QLabel("Rent (1 RR):"), row, 0)
            details_layout.addWidget(QLabel(f"${rents[0]}"), row, 1)
            row += 1
            details_layout.addWidget(QLabel("Rent (2 RR):"), row, 0)
            details_layout.addWidget(QLabel(f"${rents[1]}"), row, 1)
            row += 1
            details_layout.addWidget(QLabel("Rent (3 RR):"), row, 0)
            details_layout.addWidget(QLabel(f"${rents[2]}"), row, 1)
            row += 1
            details_layout.addWidget(QLabel("Rent (4 RR):"), row, 0)
            details_layout.addWidget(QLabel(f"${rents[3]}"), row, 1)
            row += 1
        
        elif space_type == "UTILITY":
            details_layout.addWidget(QLabel(""), row, 0)
            row += 1
            details_layout.addWidget(QLabel("Rent (1 Utility):"), row, 0)
            details_layout.addWidget(QLabel("4× dice roll"), row, 1)
            row += 1
            details_layout.addWidget(QLabel("Rent (2 Utilities):"), row, 0)
            details_layout.addWidget(QLabel("10× dice roll"), row, 1)
            row += 1
        
        # Mortgage value
        if cost:
            mortgage_value = cost // 2
            details_layout.addWidget(QLabel("Mortgage Value:"), row, 0)
            details_layout.addWidget(QLabel(f"${mortgage_value}"), row, 1)
            row += 1
        
        layout.addWidget(details)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
