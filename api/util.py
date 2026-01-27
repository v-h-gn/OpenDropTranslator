
from enum import Enum
from typing import NamedTuple

class Position(NamedTuple):
    """Position on the OpenDrop chip grid."""
    x: int
    y: int

    def get_neighbors(self) -> list["Position"]:
        """Get neighboring positions (up, down, left, right)."""
        return [
            Position(self.x + 1, self.y),
            Position(self.x - 1, self.y),
            Position(self.x, self.y + 1),
            Position(self.x, self.y - 1),
        ]

    def valid(self, board_size: tuple[int, int]) -> bool:
        """Check if position is within board boundaries."""
        return 0 <= self.x < board_size[0] and 0 <= self.y < board_size[1]

    def get_valid_neighbors(self, board_size: tuple[int, int]) -> list["Position"]:
        """Get valid neighboring positions within board boundaries."""
        return [p for p in self.get_neighbors() if p.valid(board_size)]

    def manhattan_distance(self, other: "Position") -> int:
        """Calculate Manhattan distance to another position."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    @staticmethod
    def irv(pos1: "Position | None", pos2: "Position | None") -> bool:
        """Interference Region Violation (IRV) check between two positions."""
        if pos1 is None or pos2 is None:
            return False

        return abs(pos1.x - pos2.x) <= 1 and abs(pos1.y - pos2.y) <= 1
    
class Droplet(NamedTuple):
    """Represents a type of fluid used in operations."""
    id: str  # Unique identifier for the droplet
    concentration: int  # Concentration of the fluid
    volume: int = 1  # Volume in location units
    denominator: int = 256  # Denominator for concentration (e.g., 1/denominator)
    
    def __str__(self) -> str:
        return f"Droplet(id={self.id}, concentration={self.concentration/self.denominator}, volume={self.volume})"
    
class Type(Enum):
    MIX = "mix"
    HEAT = "heat"
    DETECT = "detect"
    INPUT_0 = "input-0"
    INPUT_1 = "input-1"
    OUTPUT = "output"
    STORAGE = "storage"
    WASTE = "waste"