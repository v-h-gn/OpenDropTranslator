import json

from dataclasses import dataclass
from util import Position

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
    entrances: list[Position]
    exits: list[Position]
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

    def store(self) -> Position:
        """Store a droplet in the module's storage. Returns entrance position."""
        index = self.storage.stored_droplets
        self.storage.store()
        return self.entrances[index]

    def retrieve(self) -> Position:
        """Retrieve a droplet from the module's storage. Returns exit position."""
        self.storage.retrieve()
        return self.exits[self.storage.stored_droplets]

    @staticmethod
    def mods_by_type(modules: list["Module"]) -> dict[str, list["Module"]]:
        """Generate a map of module types to lists of Module instances."""
        modules_by_type: dict[str, list["Module"]] = {}
        for mod in modules:
            if mod.type not in modules_by_type:
                modules_by_type[mod.type] = []
            modules_by_type[mod.type].append(mod)
        return modules_by_type

    def __repr__(self) -> str:
        return f"Module({self.id}-{self.type})"


class Storage(Module):
    """Storage module with increased capacity."""

    def __init__(self, id: str, location: Position, capacity: int = 1):
        super().__init__(
            pos=location,
            id=id,
            type="storage",
            entrances=[location],
            exits=[location],
            storage=Holder(capacity=capacity),
        )


class Reservoir(Module):
    """Abstraction of I/O reservoir modules"""

    def __init__(self, id: str, location: Position, capacity: int):
        super().__init__(
            pos=location,
            id=id,
            type="reservoir",
            entrances=[location],
            exits=[location],
            storage=Holder(capacity=capacity),
        )
        self.storage.stored_droplets = capacity  # Reservoirs start full


class InputModule(Reservoir):
    """Input reservoir module"""

    def __init__(self, id: str, location: Position, capacity: int = 3):
        super().__init__(id=id, location=location, capacity=capacity)
        self.type = "input"


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

def load_modules(filename: str) -> list[Module]:
    """Load module definitions from a JSON file."""
    modules_list: list[Module] = []

    with open(filename, "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:
            module = None
            if mod["type"] == "waste":
                module = WasteModule(
                    id=mod["id"],
                    location=Position(*mod["pos"]),
                    capacity=mod.get("capacity", 6),
                )
            elif mod["type"].startswith("input"):
                module = InputModule(
                    id=mod["id"],
                    location=Position(*mod["pos"]),
                    capacity=mod.get("capacity", 3),
                )
            elif mod["type"].startswith("output"):
                module = OutputModule(
                    id=mod["id"],
                    location=Position(*mod["pos"]),
                    capacity=mod.get("capacity", 3),
                )
            elif mod["type"] == "storage":
                module = Storage(
                    id=mod["id"],
                    location=Position(*mod["pos"]),
                    capacity=mod.get("capacity", 2),
                )
            else:
                module = Module(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=mod["type"],
                    entrances=[Position(*entr) for entr in mod["entrances"]],
                    exits=[Position(*exit) for exit in mod["exits"]],
                    storage=Holder(capacity=mod.get("storage", 0)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1),
                )
            modules_list.append(module)

    return modules_list
