from dataclasses import dataclass, field

from enum import Enum
import json

from api.util import Position, Type, path_find, get_frames


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


class Port(Enum):
    UNUSED = 0
    ENTRANCE = 1
    EXIT = 2


@dataclass(eq=True)
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
    load_time: int = 0
    exec_time: int = 0
    stop_time: int = 0
    load_animation: str = "load_animation.json"
    exec_animation: str = "exec_animation.json"
    stop_animation: str = "stop_animation.json"
    used_ports: dict[Position, list[Port]] = field(default_factory=dict[Position, list[Port]])

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
        return [p for p in self.ports if self.used_ports[p][tick] == Port.UNUSED]

    def reset_ports(self) -> None:
        """Reset all ports to unused."""
        # Size arrays with generous buffer to account for delays during protocol conversion
        # Operations can be delayed significantly if droplets arrive at different times
        array_size = max(self.end_time + 50, 400)  # At least 200 to handle delays
        for port in self.ports:
            self.used_ports[port] = [Port.UNUSED] * array_size

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Module):
            return False
        return self.id == value.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __load_animation__(self, tick: int, start: int, end: int) -> set[Position]:
        """Generate the set of positions occupied by the droplet during the loading phase of this operation at a given tick."""
        return set()

    def __exec_animation__(self, tick: int, start: int, end: int) -> set[Position]:
        """Generate the set of positions occupied by the droplet during this operation at a given tick."""
        return set()

    def __stop_animation__(self, tick: int, start: int, end: int) -> set[Position]:
        """Generate the set of positions occupied by the droplet during the stopping phase of this operation at a given tick."""
        return set()

    def animation(self, tick: int, start: int = 0, end: int = 0) -> set[Position]:
        duration = self.load_time + self.exec_time + self.stop_time
        if 0 <= tick - start < self.load_time:
            return self.__load_animation__(tick - start, start, end)
        elif self.load_time <= tick - start < self.load_time + self.exec_time:
            return self.__exec_animation__(tick - start, start, end)
        elif self.load_time + self.exec_time <= tick - start < duration:
            return self.__stop_animation__(tick - start, start, end)
        else:
            raise ValueError(
                f"Tick {tick} is out of bounds for operation starting at {start} with duration {duration}."
            )

    @staticmethod
    def mods_by_type(modules: list["Module"]) -> dict[Type, list["Module"]]:
        """Generate a map of module types to lists of Module instances."""
        modules_by_type: dict[Type, list["Module"]] = {}
        for mod in modules:
            if mod.type not in modules_by_type:
                modules_by_type[mod.type] = []
            modules_by_type[mod.type].append(mod)
        return modules_by_type
    
    @staticmethod
    def get_nearest_ports(parent: "Module", child: "Module", tick1: int, tick2: int) -> tuple[Position, Position]:
        """Get the closest unused entrance/exit pairs for the given module."""
        unused_parent_ports = parent.get_unused_ports(tick1)
        unused_child_ports = child.get_unused_ports(tick2)

        pairs = [(p1, p2) for p1 in unused_parent_ports for p2 in unused_child_ports]

        return min(pairs, key=lambda pair: pair[0].manhattan_distance(pair[1]))


@dataclass
class StorageModule(Module):
    """Represents a storage operation."""

    def animation(self, tick: int, start: int = 0, end: int = 0) -> set[Position]:
        return {self.pos}

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass
class ReservoirModule(Module):
    """Represents a reservoir operation."""


@dataclass
class InputModule(ReservoirModule):
    """Represents an input operation."""

    load_time: int = 0
    exec_time: int = 6
    stop_time: int = 0
    duration: int = load_time + exec_time + stop_time

    def __exec_animation__(self, tick: int, start: int = 0, end: int = 0) -> set[Position]:
        dispense_frames = get_frames(self.exec_animation)
        return dispense_frames[tick]

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass
class OutputModule(ReservoirModule):
    """Represents an output operation."""

    load_time: int = 1
    exec_time: int = 0
    stop_time: int = 0
    duration: int = load_time + exec_time + stop_time

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass
class WasteModule(ReservoirModule):
    """Represents a waste operation."""

    load_time: int = 1
    exec_time: int = 0
    stop_time: int = 0
    duration: int = load_time + exec_time + stop_time

    def __load_animation__(self, tick: int, start: int, end: int) -> set[Position]:
        return get_frames(self.load_animation)[tick]

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass
class MixModule(Module):
    """Represents a mixing operation."""

    load_time: int = 1
    exec_time: int = 12
    stop_time: int = 3
    duration: int = load_time + exec_time + stop_time

    def __load_animation__(self, tick: int, start: int = 0, end: int = 0) -> set[Position]:
        # Droplets are at ports, need to be moved to center
        used_ports = [port for port in self.ports if self.used_ports[port][start] == Port.ENTRANCE]
        nearest_internal_positions = [self.get_nearest_internal_pos(port) for port in used_ports]
        return set(nearest_internal_positions)

    def __exec_animation__(self, tick: int, start: int = 0, end: int = 0) -> set[Position]:
        frames = [
            {
                self.pos + Position(0, 0),
                self.pos + Position(1, 0),
            },  # top-right (right in x)
            {
                self.pos + Position(1, 0),
                self.pos + Position(2, 0),
            },  # top-right (right in x
            {
                self.pos + Position(2, 0),
                self.pos + Position(2, 1),
            },  # bottom-right (down in y)
            {
                self.pos + Position(2, 1),
                self.pos + Position(1, 1),
            },  # bottom-left (left in x)
            {
                self.pos + Position(1, 1),
                self.pos + Position(0, 1),
            },  # bottom-left (down in x)
            {
                self.pos + Position(0, 1),
                self.pos + Position(0, 0),
            },  # top-left (down in y)
        ]
        return frames[tick % 6]

    def __stop_animation__(self, tick: int, start: int = 0, end: int = 0) -> set[Position]:
        # Handle splitting animation and moving to exit ports
        frame_idx = tick - self.load_time - self.exec_time

        # Look for EXIT ports at end time - the port marking shifts with operation delays
        exits = [
            port for port in self.ports if end < len(self.used_ports[port]) and self.used_ports[port][end] == Port.EXIT
        ]

        # If no external exits, droplets are likely being transferred internally
        # (all children on same module). Keep droplets in the module.
        assert (
            exits
        ), f"MixModule {self.id} has no EXIT ports at end time {end}. Check for internal transfers or scheduling issues."

        if frame_idx == 0:
            return {self.pos + Position(0, 0), self.pos + Position(2, 0)}
        if frame_idx >= 1:
            if(len(exits) == 2):
                nearest_exit_left = min(
                    exits,
                    key=lambda port: port.manhattan_distance(self.pos + Position(0, 0)),
                )
                nearest_exit_right = min(
                    exits,
                    key=lambda port: port.manhattan_distance(self.pos + Position(2, 0)),
                )

                route_left = path_find(self.pos + Position(0, 0), nearest_exit_left, set())
                route_right = path_find(self.pos + Position(2, 0), nearest_exit_right, set())

                return {
                    (route_left[frame_idx - 1] if frame_idx - 1 < len(route_left) else nearest_exit_left),
                    (route_right[frame_idx - 1] if frame_idx - 1 < len(route_right) else nearest_exit_right),
                }
            else:
                nearest_exit = exits[0]

                nearest_droplet_pos = self.pos + Position(0, 0) if nearest_exit.manhattan_distance(self.pos + Position(0, 0)) < nearest_exit.manhattan_distance(self.pos + Position(2, 0)) else self.pos + Position(2, 0)
                route = path_find(nearest_droplet_pos, nearest_exit, set())

                return {
                    (route[frame_idx - 1] if frame_idx - 1 < len(route) else nearest_exit),
                    (self.pos + Position(2, 0) if nearest_droplet_pos == self.pos + Position(0, 0) else self.pos + Position(0, 0)),
                }
        else:
            raise ValueError(f"Invalid frame index {frame_idx} for stop animation of MixModule {self.id}.")

    def __repr__(self) -> str:
        return f"Module: {self.id}, Type: {self.type}"

    def __str__(self) -> str:
        return self.__repr__()


def load_modules(filename: str) -> list[Module]:
    """Load module definitions from a JSON file."""
    modules_list: list[Module] = []

    with open(filename, "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:

            type = Type(mod["type"])
            module = None
            # If module is a reservoir type
            if type == Type.INPUT_0 or type == Type.INPUT_1:
                module = InputModule(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 6)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 0),
                    load_animation=mod["load_animation"],
                    exec_animation=mod["exec_animation"],
                    stop_animation=mod["stop_animation"],
                )
                module.storage.stored_droplets = module.storage.capacity
            elif type == Type.OUTPUT:
                module = OutputModule(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 3)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 0),
                    load_animation=mod["load_animation"],
                    exec_animation=mod["exec_animation"],
                    stop_animation=mod["stop_animation"],
                )
            elif type == Type.WASTE:
                module = WasteModule(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 6)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 0),
                    load_animation=mod["load_animation"],
                    exec_animation=mod["exec_animation"],
                    stop_animation=mod["stop_animation"],
                )
            elif type == Type.MIX:
                module = MixModule(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 1)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1),
                    load_animation=mod["load_animation"],
                    exec_animation=mod["exec_animation"],
                    stop_animation=mod["stop_animation"],
                )
            elif type == Type.STORAGE:
                module = StorageModule(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=Type(mod["type"]),
                    ports=[Position(*port) for port in mod["ports"]],
                    storage=Holder(capacity=mod.get("storage", 1)),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 0),
                    load_animation=mod.get("load_animation", "load_animation.json"),
                    exec_animation=mod.get("exec_animation", "exec_animation.json"),
                    stop_animation=mod.get("stop_animation", "stop_animation.json"),
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
                    pad=mod.get("pad", 0),
                    load_animation=mod.get("load_animation", "load_animation.json"),
                    exec_animation=mod.get("exec_animation", "exec_animation.json"),
                    stop_animation=mod.get("stop_animation", "stop_animation.json"),
                )

            modules_list.append(module)

    return modules_list
