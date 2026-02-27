import copy
from enum import Enum
from collections import deque
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
    
    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"

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
    INVALID = "invalid"

def get_frames(animation_file: str = "dispense.json", board_size: tuple[int, int] = (16, 8)) -> list[set[Position]]:
    """
    Load animation frames from a specific animation file dispense.json.
    
    Args:
        animation_file (str): Path to the animation file
        board_size (tuple[int, int]): Size of the board (width, height)
    
    Returns:
        list[set[Position]]: List of 6 frame sets with active positions.
    """
    height = board_size[1]
    width = board_size[0]
    protocol = [set[Position]() for _ in range(6)]  # 6 dispense frames
    import json

    # Load dispense.json
    with open(animation_file, "r") as f:
        all_frames = json.load(f)
    
    # Extract the frames for this reservoir
    dispense_frames = all_frames
    
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

def path_find(
    src: Position,
    dst: Position,
    no_go_cells: set[Position] = set(),
    board_size: tuple[int, int] = (16, 8),
) -> list[Position]:
    """Finds a route from src to dst using Lee's algorithm."""
    init_route = (src, src, [src])
    q = deque([init_route])
    visited = {src}
    route = init_route
    while q:
        route = q.popleft()
        route_src, route_dst, route_path = route
        if route_dst == dst:
            return route_path
        for neighbor in route_dst.get_valid_neighbors(board_size):
            if neighbor not in visited and neighbor not in no_go_cells:
                visited.add(neighbor)
                new_route = (route_src, neighbor, copy.deepcopy(route_path) + [neighbor])
                q.append(new_route)
    raise RuntimeError(f"No route found from {src} to {dst}")

def pos_to_reservoir(pos: Position) -> str:
    """Convert a position to a reservoir name."""
    if pos == Position(1, 1):
        return "top_left"
    elif pos == Position(14, 1):
        return "top_right"
    elif pos == Position(1, 6):
        return "bottom_left"
    elif pos == Position(14, 6):
        return "bottom_right"
    else:
        return "invalid"