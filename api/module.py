import json

from dataclasses import dataclass, field
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
        self.stored_droplets += 1

    def retrieve(self) -> None:
        """Retrieve a droplet if there are any stored."""
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
    ports: list[Position]
    storage: Holder
    end_time: int = 0
    width: int = 3
    height: int = 3
    pad: int = 1
    used_ports: dict[Position, bool] = field(default_factory=dict[Position, bool])
    
    def __post_init__(self) -> None:
        self.used_ports = {port: False for port in self.ports}

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

    def get_nearest_ports(self, other_mod: "Module") -> tuple[Position, Position]:
        """Get the closest unused entrance/exit pairs for the given module."""
        unused_self_ports = self.get_unused_ports()
        unused_other_ports = other_mod.get_unused_ports()

        pairs = [(p1, p2) for p1 in unused_self_ports for p2 in unused_other_ports]
 
        return min(pairs, key=lambda pair: pair[0].manhattan_distance(pair[1]))

    def get_unused_ports(self) -> list[Position]:
        """Get a list of unused ports for the module."""
        return [p for p in self.ports if not self.used_ports[p]]
    
    def reset_ports(self) -> None:
        """Reset all ports to unused."""
        for port in self.used_ports:
            self.used_ports[port] = False

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    @staticmethod
    def mods_by_type(modules: list["Module"]) -> dict[Type, list["Module"]]:
        """Generate a map of module types to lists of Module instances."""
        modules_by_type: dict[Type, list["Module"]] = {}
        for mod in modules:
            if mod.type not in modules_by_type:
                modules_by_type[mod.type] = []
            modules_by_type[mod.type].append(mod)
        return modules_by_type

def load_modules(filename: str) -> list[Module]:
    """Load module definitions from a JSON file."""
    modules_list: list[Module] = []

    with open(filename, "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:
            
            type = Type(mod["type"])

            # If module is a reservoir type
            if type == Type.INPUT_0 or type == Type.INPUT_1:
                module = Module(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 6)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 0),
                )
                module.storage.stored_droplets = module.storage.capacity
            elif type == Type.OUTPUT or type == Type.WASTE:
                module = Module(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 6)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 0),
                )
            else:
                module = Module(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 1)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1),
                )
                
            modules_list.append(module)

    return modules_list
