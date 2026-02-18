
from dataclasses import dataclass

from api.util import Position, Type
from api.module import Module

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

    def print_route(self, board_size: tuple[int, int] = (16, 8), no_go_cells: set[Position] = set(), modules: list[Module] = list()) -> None:
        """Prints a visual representation of the route on the board."""
        board = [["." for _ in range(board_size[1])] for _ in range(board_size[0])]

        for cell in no_go_cells:
            if cell.valid(board_size):
                board[cell.x][cell.y] = "#"

        for step in self.path:
            if step.valid(board_size):
                board[step.x][step.y] = "*"
            if step == self.src and step.valid(board_size):
                board[step.x][step.y] = "0"
            if step == self.dst and step.valid(board_size):
                board[step.x][step.y] = "1"

        for mod in modules:
            for x in range(mod.pos.x, mod.pos.x + mod.width):
                for y in range(mod.pos.y, mod.pos.y + mod.height):
                    if Position(x, y).valid(board_size):

                        if mod.type == Type.INPUT_0 or mod.type == Type.INPUT_1:
                            board[x][y] = "I"
                        elif mod.type == Type.OUTPUT:
                            board[x][y] = "O"
                        elif mod.type == Type.WASTE:
                            board[x][y] = "W"
                        elif mod.type == Type.MIX:
                            board[x][y] = "M"
                        elif mod.type == Type.STORAGE:
                            board[x][y] = "S"
                        elif mod.type == Type.HEAT:
                            board[x][y] = "H"
                        elif mod.type == Type.DETECT:
                            board[x][y] = "D"

                        if Position(x, y) in mod.ports:
                            board[x][y] = "P"
    
        # take transpose of board
        board_t = list(zip(*board))

        for row in board_t:
            print(" ".join(row))
        print()