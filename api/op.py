from dataclasses import dataclass, field
from typing import Callable
from networkx.drawing.nx_pydot import read_dot

from api.util import Position, Type, get_dispense_frames
from api.module import Module
from translator import RESERVOIR_RANGES
from translator import RESERVOIR_RANGES

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

    id: str  # M1
    type: Type
    duration: int
    start_time: int = -1  # START TIME
    end_time: int = -1  # END TIME
    size: int = 1  # SIZE OF DROPLET
    bound: bool = False  # HAS MODULE
    parents: list["Op"] = field(default_factory=list["Op"])  # PARENT OPERATIONS
    children: list["Op"] = field(default_factory=list["Op"])  # CHILD OPERATIONS
    module: Module | None = None

    def parents_scheduled(
        self, excluding: Callable[["Op"], bool] | None = None
    ) -> bool:
        """Check if all parent operations are scheduled"""
        if excluding is None:
            return all(parent.is_scheduled() for parent in self.parents)
        return all(
            parent.is_scheduled() or excluding(parent) for parent in self.parents
        )

    def delay(self, ticks: int, propagate: bool = True) -> None:
        """Delay the operation and (optionally) all operations that depend on it by a given number of ticks."""
        if propagate and self.children:
            for child in self.children:
                child.delay(ticks)
        self.start_time += ticks
        self.end_time += ticks

    def critical_path_length(self) -> int:
        """Calculate the length of the critical path from this operation to the end."""
        if not self.children:
            return self.duration
        return self.duration + max(
            child.critical_path_length() for child in self.children
        )

    def is_scheduled(self) -> bool:
        """Check if the operation has been scheduled."""
        return self.start_time != -1 and self.end_time != -1

    def __str__(self) -> str:
        return f"Op {self.id} of type {self.type} runs from {self.start_time}-{self.end_time} on module {self.module}"

    def __repr__(self) -> str:
        return f"Op({self.id}-{self.type})"

    def __hash__(self) -> int:
        return hash(self.id)
    
    @staticmethod
    def ops_by_type(ops: list["Op"]) -> dict[Type, list["Op"]]:
        """Generate a map of module types to lists of Op instances."""
        ops_by_type: dict[Type, list["Op"]] = {}
        for op in ops:
            if op.type not in ops_by_type:
                ops_by_type[op.type] = []
            ops_by_type[op.type].append(op)
        return ops_by_type


class StorageOp(Op):
    """Represents a storage operation."""

    def __init__(self, id: str, duration: int):
        super().__init__(id=id, type=Type.STORAGE, duration=duration)

    def animation(self, anchor: Position, tick: int, args: None = None) -> set[Position]:
        return {anchor}


class ReservoirOp(Op):
    """Represents a reservoir operation."""

    def __init__(self, id: str, type: Type, duration: int):
        super().__init__(id=id, type=type, duration=duration)


class InputOp(ReservoirOp):
    """Represents an input operation."""

    def __init__(self, id: str, input_type: Type, duration: int):
        super().__init__(id=id, type=input_type, duration=duration)

    def exec_animation(self, anchor: Position, tick: int) -> set[Position]:
        dispense_frames = get_dispense_frames(anchor, RESERVOIR_RANGES)

        return dispense_frames[tick]
    
class OutputOp(ReservoirOp):
    """Represents an output operation."""

    def __init__(self, id: str, duration: int):
        super().__init__(id=id, type=Type.OUTPUT, duration=duration)

class WasteOp(ReservoirOp):
    """Represents a waste operation."""

    def __init__(self, id: str, duration: int):
        super().__init__(id=id, type=Type.WASTE, duration=duration)


class MixOp(Op):
    """Represents a mixing operation."""

    def __init__(self, id: str, duration: int):
        super().__init__(id=id, type=Type.MIX, duration=duration)
        self.split_tick = self.start_time + duration - 4  # Last 4 ticks are for splitting
        self.load_tick = self.start_time + 1  # First tick is for moving droplets from ports to center

    def animation(self, anchor: Position, tick: int) -> set[Position]:
        x0, y0 = anchor.x, anchor.y
        frames = [
            Position(x0 + 1, y0),  # top-right (right in x)
            Position(x0 + 1, y0 + 1),  # bottom-right (up in y)
            Position(x0, y0 + 1),  # bottom-left (down in x)
            Position(x0, y0),  # top-left (down in y)
        ]
        return {frames[tick % 4]}


def load_ops_from_dot(filepath: str):
    op_graph = read_dot(filepath)
    op_dict: dict[str, Op] = {}
    mixing_ops: list[str] = []

    # CREATE ALL THE OPERATIONS
    for nid, attrs in op_graph.nodes(data=True):
        label = (attrs.get("label") or "").strip('"')
        if label == "mix":
            op_dict[nid] = MixOp(nid, duration=16)
            mixing_ops.append(nid)
        elif label == "(0,1)":
            op_dict[nid] = InputOp(nid, duration=6, input_type=Type.INPUT_0)
        elif label == "(1,1)":
            op_dict[nid] = InputOp(nid, duration=6, input_type=Type.INPUT_1)
        else:
            raise ValueError(f"Unknown operation label: {label}")

    # CONNECT PARENTS AND CHILDREN
    for src, dst in op_graph.edges():
        op_dict[src].children.append(op_dict[dst])
        op_dict[dst].parents.append(op_dict[src])

    # ADD WASTE AND OUTPUT NODES FOR MIX OPERATIONS
    for nid in mixing_ops:
        child_count = len(op_dict[nid].children)
        if child_count == 1:
            waste_operation = WasteOp("waste_" + nid, duration=1)
            op_dict[waste_operation.id] = waste_operation
            op_dict[nid].children.append(waste_operation)
            waste_operation.parents.append(op_dict[nid])
        elif child_count == 0:
            output_operation = OutputOp("output_" + nid, duration=1)
            op_dict[output_operation.id] = output_operation
            op_dict[nid].children.append(output_operation)
            output_operation.parents.append(op_dict[nid])
    operations_list = list(op_dict.values())

    return sorted(operations_list, key=lambda o: o.critical_path_length(), reverse=True)
