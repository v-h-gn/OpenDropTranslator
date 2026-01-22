from typing import NamedTuple
from dataclasses import dataclass, field

@dataclass(eq=True)
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

    @staticmethod
    def irv(pos1: "Position | None", pos2: "Position | None") -> bool:
        """Interference Region Violation (IRV) check between two positions."""
        if pos1 is None or pos2 is None:
            return False

        return abs(pos1.x - pos2.x) <= 1 and abs(pos1.y - pos2.y) <= 1

@dataclass(eq=True)
class Op:  # OPERATION IN SCHEDULE
    """
    Represents an operation to be performed on the OpenDrop chip.

    Attributes:
        name (str): The name of the operation.
        type (str): The type of operation (e.g., mix, heat).
        duration (int): The duration of the operation.
        start_time (int): The start time of the operation.
        end_time (int): The end time of the operation.
        size (int): The size of the droplet involved in the operation.
        module (str): The module assigned to perform the operation.
        bound (bool): Indicates whether the operation has been bound to a module.
        parents (list[Op]): List of parent operations.
        children (list[Op]): List of child operations.
    """
    name: str  # M1
    type: str  # MIX HEAT
    duration: int
    start_time: int = -1  # START TIME
    end_time: int = -1  # END TIME
    size: int = 1  # SIZE OF DROPLET
    module: str = ""  # WHICH MODULE IT IS ASSIGNED TO
    bound: bool = False  # HAS MODULE
    parents: list["Op"] = field(default_factory=list["Op"])  # PARENT OPERATIONS
    children: list["Op"] = field(default_factory=list["Op"])  # CHILD OPERATIONS

    def parents_scheduled(self) -> bool:
        """Check if all parent operations are scheduled"""
        return all(parent.is_scheduled() for parent in self.parents)
    
    def delay(self, ticks: int) -> None:
        """Delay the operation and all operations that depend on it by a given number of ticks."""
        if self.children:
            for child in self.children:
                child.delay(ticks)
        self.start_time += ticks
        self.end_time += ticks
    
    def critical_path_length(self) -> int:
        """Calculate the length of the critical path from this operation to the end."""
        if not self.children:
            return self.duration
        return self.duration + max(child.critical_path_length() for child in self.children)
    
    def is_scheduled(self) -> bool:
        """Check if the operation has been scheduled."""
        return self.start_time != -1 and self.end_time != -1

    def is_input(self) -> bool:
        """Check if the operation is an input operation."""
        return self.type.startswith("input")

    def input_type(self) -> str:
        """Get the specific type of input operation."""
        if self.is_input():
            return self.type.split("-")[-1]
        raise RuntimeError("Operation is not an input operation.")

    def __str__(self) -> str:
        return f"Op({self.name}, {self.type}, {self.start_time}-{self.end_time}, module={self.module})"

    def __repr__(self) -> str:
        return f"Op({self.name}-{self.type})"

    def __hash__(self) -> int:
        return hash(self.name)
    
    @staticmethod
    def ops_by_type(ops: list["Op"]) -> dict[str, list["Op"]]:
        """Generate a map of module types to lists of Op instances."""
        ops_by_type: dict[str, list["Op"]] = {}
        for op in ops:
            if op.type not in ops_by_type:
                ops_by_type[op.type] = []
            ops_by_type[op.type].append(op)
        return ops_by_type

    
    
@dataclass
class Holder:  # STORAGE CAPACITY FOR MODULE
    """Represents storage capacity for a module."""
    capacity: int = 2  # HOW MANY DROPLETS
    stored_droplets: int = 0

    def has_space(self) -> bool:
        """Check if there is available storage space."""
        return self.stored_droplets < self.capacity
    
    def store(self) -> None:
        """Store a droplet if there is space."""
        if not self.has_space():
            raise RuntimeError("No storage space available.")
        self.stored_droplets += 1
    
    def retrieve(self) -> None:
        """Retrieve a droplet if there are any stored."""
        if self.stored_droplets <= 0:
            raise RuntimeError("No droplets to retrieve.")
        self.stored_droplets -= 1
    
@dataclass
class Module: 
    """
    Represents a module on microfluidic chip.

    Attributes:
        pos (Position): The position of the module on the chip.
        id (str): The unique identifier for the module.
        type (str): The type of the module (e.g., mix, heat).
        entrance (Position): The entrance position for droplets entering the module.
        exit (Position): The exit position for droplets leaving the module.
        end_time (int): The end time of the last operation assigned to this module.
        width (int): The width of the module.
        height (int): The height of the module.
        pad (int): The padding around the module for routing.
    """
    pos: Position
    id: str  
    type: str 
    entrance: Position 
    exit: Position 
    storage: Holder
    end_time: int = 0  
    width: int = 3
    height: int = 3
    pad: int = 1 

    def available(self, tick: int) -> bool:
        """Check if the module is free at the given tick."""
        return self.end_time <= tick

    def empty(self) -> bool:
        """Check if the module has no stored droplets."""
        return self.storage.stored_droplets == 0
    
    def full(self) -> bool:
        """Check if the module's storage is full."""
        return not self.storage.has_space()
    
    def has_space(self) -> bool:
        """Check if the module has storage space available."""
        return self.storage.has_space()
    
    @staticmethod
    def mods_by_type(modules: list["Module"]) -> dict[str, list["Module"]]:
        """Generate a map of module types to lists of Module instances."""
        modules_by_type: dict[str, list["Module"]] = {}
        for mod in modules:
            if mod.type not in modules_by_type:
                modules_by_type[mod.type] = []
            modules_by_type[mod.type].append(mod)
        return modules_by_type

class Storage(Module):
    """Storage module with increased capacity."""
    def __init__(self, id: str, location: Position, capacity: int = 1):
        super().__init__(pos=location, id=id, type="storage", entrance=location, exit=location, storage=Holder(capacity=capacity))

class Reservoir(Module):
    """Abstraction of I/O reservoir modules"""
    def __init__(self, id: str, location: Position, capacity: int):
        super().__init__(pos=location, id=id, type="reservoir", entrance=location, exit=location, storage=Holder(capacity=capacity))

class InputModule(Reservoir):
    """Input reservoir module"""
    def __init__(self, id: str, location: Position, capacity: int = 3):
        super().__init__(id=id, location=location, capacity=capacity)
        self.type ="input"

class OutputModule(Reservoir):
    """Output reservoir module"""
    def __init__(self, id: str, location: Position, capacity: int = 3):
        super().__init__(id=id, location=location, capacity=capacity)
        self.type = "output"

class WasteModule(Reservoir):
    """Waste reservoir module"""
    def __init__(self, id: str, location: Position, capacity: int = 10):
        super().__init__(id=id, location=location, capacity=capacity)
        self.type = "waste"

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
        return (
            self.src == value.src and self.dst == value.dst and self.path == value.path
        )
