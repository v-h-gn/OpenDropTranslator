
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


def convert_to_protocol(positions: set[Position], board_size: tuple[int, int] = (17, 8)) -> list[str]:
    """Convert a set of positions to a protocol string.
    Args:
        positions (set[Position]): Set of positions to convert.
    Returns:
        list[str]: Protocol strings representing the positions.

    The protocol string format is a list of strings of zeros and ones, where '1' indicates
    an on electrode at that position and '0' indicates off. Each list element corresponds to a row.    
    """
    rows = ["0" * board_size[0] for _ in range(board_size[1])]

    for pos in positions:
        row = list(rows[pos.y])
        row[pos.x] = "1"
        rows[pos.y] = "".join(row)

    return rows


def get_dispense_frames(reservoir: Position, reservoir_ranges: dict[Position, tuple[int, int]], dispense_file: str = "dispense.json") -> list[dict[str, str | int]]:
    """
    Load dispense animation frames for a specific reservoir from dispense.json.
    
    Args:
        reservoir (Position): Reservoir position - one of Position(1,1), Position(14,1), Position(1,6), Position(14,6)
        dispense_file (str): Path to the dispense.json file
    
    Returns:
        list[dict]: List of 6 frame dictionaries with y0-y7 electrode states and frame numbers.
        
    Dispense animations are stored in dispense.json as:
    - top_left: frames 1-6 (indices 0-5)
    - top_right: frames 7-12 (indices 6-11)
    - bottom_left: frames 13-18 (indices 12-17)
    - bottom_right: frames 19-24 (indices 18-23)
    """
    import json
    
    if reservoir not in reservoir_ranges:
        raise ValueError(f"Invalid reservoir: {reservoir}. Must be one of {list(reservoir_ranges.keys())}")
    
    # Load dispense.json
    with open(dispense_file, "r") as f:
        all_frames = json.load(f)
    
    # Extract the frames for this reservoir
    start_idx, end_idx = reservoir_ranges[reservoir]
    return all_frames[start_idx:end_idx]