from enum import Enum
from typing import NamedTuple, cast

from api.op import Op
from api.route import Route
from api.module import Module

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
    
    def __sub__(self, other: "Position") -> "Position":
        """Subtract two positions."""
        return Position(self.x - other.x, self.y - other.y)
    
    def __add__(self, other: "Position") -> "Position":
        """Add two positions."""
        return Position(self.x + other.x, self.y + other.y)

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

def get_dispense_frames(reservoir: Position, reservoir_ranges: dict[Position, tuple[int, int]], animation_file: str = "dispense.json", board_size: tuple[int, int] = (16, 8)) -> list[set[Position]]:
    """
    Load dispense animation frames for a specific reservoir from dispense.json.
    
    Args:
        reservoir (Position): Reservoir position - one of Position(1,1), Position(14,1), Position(1,6), Position(14,6)
        dispense_file (str): Path to the dispense.json file
    
    Returns:
        list[set[Position]]: List of 6 frame sets with active positions.
        
    Dispense animations are stored in dispense.json as:
    - top_left: frames 1-6 (indices 0-5)
    - top_right: frames 7-12 (indices 6-11)
    - bottom_left: frames 13-18 (indices 12-17)
    - bottom_right: frames 19-24 (indices 18-23)
    """
    height = board_size[1]
    width = board_size[0]
    protocol = [set[Position]() for _ in range(6)]  # 6 dispense frames
    import json
    
    if reservoir not in reservoir_ranges:
        raise ValueError(f"Invalid reservoir: {reservoir}. Must be one of {list(reservoir_ranges.keys())}")
    
    # Load dispense.json
    with open(animation_file, "r") as f:
        all_frames = json.load(f)
    
    # Extract the frames for this reservoir
    start_idx, end_idx = reservoir_ranges[reservoir]
    dispense_frames = all_frames[start_idx:end_idx]
    
    # Convert frames to sets of active positions
    for idx, frame in enumerate(dispense_frames):
        # Convert frame rows to active positions, respecting current board size
        for y in range(height):
            row_key = f"y{y}"
            if row_key not in frame:
                continue
            row_str = str(frame[row_key])
            for x in range(min(width, len(row_str))):
                if row_str[x] == "1":
                    protocol[idx].add(Position(x, y))
    return protocol

def get_output_frames(reservoir: Position, reservoir_ranges: dict[Position, tuple[int, int]], animation_file: str = "animation.json") -> list[dict[str, str | int]]:
    """
    Load output animation frames for a specific reservoir from output.json.
    
    Args:
        reservoir (Position): Reservoir position - one of Position(1,1), Position(14,1), Position(1,6), Position(14,6)
        animation_file (str): Path to the animation.json file
    Returns:
        list[dict]: List of 6 frame dictionaries with y0-y7 electrode states and frame numbers.
    """

    import json
    
    if reservoir not in reservoir_ranges:
        raise ValueError(f"Invalid reservoir: {reservoir}. Must be one of {list(reservoir_ranges.keys())}")
    
    # Load output.json
    with open(animation_file, "r") as f:
        all_frames = json.load(f)
    
    # Extract the frames for this reservoir
    start_idx, end_idx = reservoir_ranges[reservoir]
    return all_frames[start_idx:end_idx]

def convert_to_protocol(ops: list[Op], modules_by_id: dict[str, Module], routes: list[tuple[Op, Op, Route]], reservoir_ranges: dict[Position, tuple[int, int]])
    """Convert scheduled operations and routes to a frame-based protocol."""

    max_tick = max(op.end_time for op in ops)

    protocol = [set[Position]() for _ in range(max_tick + 1)]

    for i in range(max_tick + 1):
        # For each tick, determine which operations are active and which routes are active
        active_ops = [op for op in ops if op.start_time <= i < op.end_time]
        active_routes = [route for route in routes if route[1].end_time <= i < route[1].end_time + len(route[2].path)]

        for active_op in active_ops:
            # Convert active operations to protocol frames
            # Input operations: play 6-frame dispense animation starting at op.start_time
            module = cast(Module, active_op.module)
            pass
        
        for active_route in active_routes: