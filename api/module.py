import json

from dataclasses import dataclass
from api.util import Position, Type


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
        type (Type): The type of the module (e.g., mix, heat).
        entrance (Position): The entrance position for droplets entering the module.
        exit (Position): The exit position for droplets leaving the module.
        end_time (int): The end time of the last operation assigned to this module.
        width (int): The width of the module.
        height (int): The height of the module.
        pad (int): The padding around the module for routing.
    """

    pos: Position
    id: str
    type: Type
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
    def mods_by_type(modules: list["Module"]) -> dict[Type, list["Module"]]:
        """Generate a map of module types to lists of Module instances."""
        modules_by_type: dict[Type, list["Module"]] = {}
        for mod in modules:
            if mod.type not in modules_by_type:
                modules_by_type[mod.type] = []
            modules_by_type[mod.type].append(mod)
        return modules_by_type

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

class Reservoir(Module):
    """Represents a reservoir module."""
    def __init__(
        self,
        pos: Position,
        id: str,
        type: Type,
        entrance: Position,
        exit: Position,
        storage: Holder,
        width: int = 3,
        height: int = 3,
        pad: int = 1,
    ):
        super().__init__(
            pos=pos,
            id=id,
            type=type,
            entrances=[entrance],
            exits=[exit],
            storage=storage,
            width=width,
            height=height,
            pad=pad,
        )
    
    def store(self) -> Position:
        """Store a droplet in the reservoir module's storage. Returns entrance position."""
        self.storage.store()
        return self.entrances[0]
    
    def retrieve(self) -> Position:
        """Retrieve a droplet from the reservoir module's storage. Returns exit position."""
        self.storage.retrieve()
        return self.exits[0]

def load_modules(filename: str) -> list[Module]:
    """Load module definitions from a JSON file."""
    modules_list: list[Module] = []

    with open(filename, "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:
            
            type = Type(mod["type"])

            # If module is a reservoir type
            if type == Type.INPUT_0 or type == Type.INPUT_1:
                module = Reservoir(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    entrance=Position(*mod["entrances"][0]),
                    exit=Position(*mod["exits"][0]),
                    storage=Holder(capacity=mod.get("storage", 6)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1),
                )
                module.storage.stored_droplets = module.storage.capacity
            elif type == Type.OUTPUT or type == Type.WASTE:
                module = Reservoir(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    entrance=Position(*mod["entrances"][0]),
                    exit=Position(*mod["exits"][0]),
                    storage=Holder(capacity=mod.get("storage", 6)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1),
                )
            else:
                module = Module(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    entrances=[Position(*entr) for entr in mod["entrances"]],
                    exits=[Position(*exit) for exit in mod["exits"]],
                    storage=Holder(capacity=mod.get("storage", 0)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1),
                )
                
            modules_list.append(module)

    return modules_list
