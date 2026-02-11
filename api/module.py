import json

from dataclasses import dataclass, field
from api.util import Position, Type, get_dispense_frames
from translator import RESERVOIR_RANGES

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
    load_time: int = 1
    exec_time: int = 1
    stop_time: int = 1
    used_ports: dict[Position, list[bool]] = field(default_factory=dict[Position, list[bool]])
    
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
    
    def is_internal(self, pos: Position) -> bool:
        """Check if a position is within the module's area."""
        return (self.pos.x <= pos.x < self.pos.x + self.width) and (self.pos.y <= pos.y < self.pos.y + self.height)

    def get_nearest_ports(self, tick: int, other_mod: "Module") -> tuple[Position, Position]:
        """Get the closest unused entrance/exit pairs for the given module."""
        unused_self_ports = self.get_unused_ports(tick)
        unused_other_ports = other_mod.get_unused_ports(tick)

        pairs = [(p1, p2) for p1 in unused_self_ports for p2 in unused_other_ports]
 
        return min(pairs, key=lambda pair: pair[0].manhattan_distance(pair[1]))

    def get_nearest_internal_pos(self, pos: Position) -> Position:
        """Get the nearest internal position from position pos."""
        internal_positions = [
            Position(x, y)
            for x in range(self.pos.x, self.pos.x + self.width)
            for y in range(self.pos.y, self.pos.y + self.height)
        ]
        return min(internal_positions, key=lambda p: p.manhattan_distance(pos))
    
    def get_padding_cells(self) -> set[Position]:
        """Get all padding cells around the module."""
        padding_cells = set[Position]()
        for x in range(self.pos.x - self.pad, self.pos.x + self.width + self.pad):
            for y in range(self.pos.y - self.pad, self.pos.y + self.height + self.pad):
                if not self.is_internal(Position(x, y)):
                    padding_cells.add(Position(x, y))
        return padding_cells

    def get_unused_ports(self, tick: int) -> list[Position]:
        """Get a list of unused ports for the module at the given tick."""
        return [p for p in self.ports if not self.used_ports[p][tick]]
    
    def reset_ports(self) -> None:
        """Reset all ports to unused."""
        for port in self.ports:
            self.used_ports[port] = [False] * (self.end_time + 1)

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"
    
    def __load_animation__(self, tick: int) -> set[Position]:
        """Generate the set of positions occupied by the droplet during the loading phase of this operation at a given tick."""
        return set()
    
    def __exec_animation__(self, tick: int) -> set[Position]:
        """Generate the set of positions occupied by the droplet during this operation at a given tick."""
        return set()
    
    def __stop_animation__(self, tick: int) -> set[Position]:
        """Generate the set of positions occupied by the droplet during the stopping phase of this operation at a given tick."""
        return set()

    def animation(self, tick: int) -> set[Position]:
        if 0 <= tick < self.load_time:
            return self.__load_animation__(tick)
        elif 0 <= tick < self.load_time + self.exec_time:
            return self.__exec_animation__(tick)
        elif 0 <= tick < self.load_time + self.exec_time + self.stop_time:
            return self.__stop_animation__(tick)
        else:
            return set()

    @staticmethod
    def mods_by_type(modules: list["Module"]) -> dict[Type, list["Module"]]:
        """Generate a map of module types to lists of Module instances."""
        modules_by_type: dict[Type, list["Module"]] = {}
        for mod in modules:
            if mod.type not in modules_by_type:
                modules_by_type[mod.type] = []
            modules_by_type[mod.type].append(mod)
        return modules_by_type

class StorageModule(Module):
    """Represents a storage operation."""

    def animation(self, tick: int) -> set[Position]:
        return {self.pos}


class ReservoirModule(Module):
    """Represents a reservoir operation."""


class InputModule(ReservoirModule):
    """Represents an input operation."""
    
    load_time = 0  
    exec_time = 6
    stop_time = 0  

    def __exec_animation__(self, tick: int) -> set[Position]:
        dispense_frames = get_dispense_frames(self.pos, RESERVOIR_RANGES)

        return dispense_frames[tick]
    
class OutputModule(ReservoirModule):
    """Represents an output operation."""

class WasteModule(ReservoirModule):
    """Represents a waste operation."""

class MixModule(ReservoirModule):
    """Represents a mixing operation."""

    load_time = 1
    exec_time = 12
    stop_time = 3

    def __exec_animation__(self, tick: int) -> set[Position]:
        x0, y0 = self.pos.x, self.pos.y
        frames = [
            Position(x0 + 1, y0),  # top-right (right in x)
            Position(x0 + 1, y0 + 1),  # bottom-right (up in y)
            Position(x0, y0 + 1),  # bottom-left (down in x)
            Position(x0, y0),  # top-left (down in y)
        ]
        return {frames[tick % 4]}




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
