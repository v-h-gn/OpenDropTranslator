from typing import NamedTuple
from dataclasses import dataclass, field

@dataclass(eq=True)
class Position(NamedTuple):
    x: int
    y: int

    def get_neighbors(self) -> list["Position"]:
        return [
            Position(self.x + 1, self.y),
            Position(self.x - 1, self.y),
            Position(self.x, self.y + 1),
            Position(self.x, self.y - 1),
        ]
    
    def valid(self, board_size: tuple[int, int]) -> bool:
        return 0 <= self.x < board_size[0] and 0 <= self.y < board_size[1]

    def get_valid_neighbors(self, board_size: tuple[int, int]) -> list["Position"]:
        return [p for p in self.get_neighbors() if p.valid(board_size)]
    
    @staticmethod
    def irv(pos1: "Position | None", pos2: "Position | None") -> bool:
        """Interference Region Violation (IRV) check between two positions."""
        if pos1 is None or pos2 is None:
            return False
        
        return abs(pos1.x - pos2.x) <= 1 and abs(pos1.y - pos2.y) <= 1
    
@dataclass(eq=True)
class Op: # OPERATION IN SCHEDULE
    name: str # M1
    type: str # MIX HEAT
    duration: int
    start: int = -1 # START TIME
    end: int = -1 # END TIME
    size: int = 1  # SIZE OF DROPLET
    module: str = "" # WHICH MODULE IT IS ASSIGNED TO
    bound: bool = False # HAS MODULE 
    parents: list["Op"] = field(default_factory=list["Op"]) # PARENT OPERATIONS
    children: list["Op"] = field(default_factory=list["Op"]) # CHILD OPERATIONS

    def parents_done(self, tick: int) -> bool:
        for parent in self.parents:
            if parent.end == -1 or parent.end > tick:
                return False
        return True
    
    def parents_done_ignore(self, tick: int, ignore: set["Op"]) -> bool:
        for parent in self.parents:
            if parent in ignore:
                continue
            if parent.end == -1 or parent.end > tick:
                return False
        return True
    
    def __str__(self) -> str:
        return f"Op({self.name}, {self.type}, {self.start}-{self.end}, module={self.module})"
    
    def __repr__(self) -> str:
        return f"Op({self.name}-{self.type})"
    
    def __hash__(self) -> int:
        return hash(self.name)

@dataclass
class Module: # CHIP MODULE
    pos: Position 
    id: str # MODULE IDENTIFIER
    type: str # MODULE TYPE 
    entrance: Position  # DROPLET ENTRANCE
    exit: Position      # DROPLET EXIT
    last_op_end: int = 0 # END TIME OF LAST OPERATION ASSIGNED TO THIS MODULE
    width: int = 3
    height: int = 3
    pad: int = 1 # PAD AROUND MODULE FOR ROUTING

@dataclass
class Holder: # STORAGE CAPACITY FOR MODULE 
    name: str
    id: str # WHICH MODULE DOES HOLDER BELONG TO
    start: int
    end: int # WHEN WINDOW IS AVAILABLE
    cap: int = 2 # HOW MANY DROPLETS  
    used: int = 0  

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
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Route):
            return False
        return self.src == value.src and self.dst == value.dst and self.path == value.path