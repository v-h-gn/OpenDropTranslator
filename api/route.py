from dataclasses import dataclass
from api.util import Position

@dataclass
class Route:
    """Droplet route from source to destination over time."""

    src: Position
    dst: Position
    path: list[Position]

    def prev(self, tick: int) -> Position | None:
        """Get droplet position at given tick - 1."""
        if tick <= 0 or tick >= len(self.path):
            return None
        return self.path[tick - 1]

    def curr(self, tick: int) -> Position | None:
        """Get droplet position at given tick."""
        if tick < 0 or tick >= len(self.path):
            return None
        return self.path[tick]

    def next(self, tick: int) -> Position | None:
        """Get droplet position at given tick + 1."""
        if tick < 0 or tick + 1 >= len(self.path):
            return None
        return self.path[tick + 1]
    
    def stall(self, tick: int) -> None:
        """Insert a stall at the given tick"""
        self.path.insert(tick, self.path[tick])

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Route):
            return False
        return (
            self.src == value.src and self.dst == value.dst and self.path == value.path
        )

    def __lt__(self, other: "Route") -> bool:
        return len(self.path) < len(other.path)