
from dataclasses import dataclass, field
from typing import Callable
from networkx.drawing.nx_pydot import read_dot



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
    type: str  # MIX HEAT
    duration: int
    start_time: int = -1  # START TIME
    end_time: int = -1  # END TIME
    size: int = 1  # SIZE OF DROPLET
    module: str = ""  # WHICH MODULE IT IS ASSIGNED TO
    bound: bool = False  # HAS MODULE
    parents: list["Op"] = field(default_factory=list["Op"])  # PARENT OPERATIONS
    children: list["Op"] = field(default_factory=list["Op"])  # CHILD OPERATIONS

    def parents_scheduled(
        self, excluding: Callable[["Op"], bool] | None = None
    ) -> bool:
        """Check if all parent operations are scheduled"""
        if excluding is None:
            return all(parent.is_scheduled() for parent in self.parents)
        return all(
            parent.is_scheduled() or excluding(parent) for parent in self.parents
        )

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
        return self.duration + max(
            child.critical_path_length() for child in self.children
        )

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

    def is_output(self) -> bool:
        """Check if the operation is an output operation."""
        return self.type.startswith("output")

    def output_type(self) -> str:
        """Get the specific type of output operation."""
        if self.is_output():
            return self.type.split("-")[-1]
        raise RuntimeError("Operation is not an output operation.")

    def is_waste(self) -> bool:
        """Check if the operation is a waste operation."""
        return self.type.startswith("waste")

    def waste_type(self) -> str:
        """Get the specific type of waste operation."""
        if self.is_waste():
            return self.type.split("-")[-1]
        raise RuntimeError("Operation is not a waste operation.")

    def __str__(self) -> str:
        return f"Op {self.id} of type {self.type} runs from {self.start_time}-{self.end_time} on module {self.module}"

    def __repr__(self) -> str:
        return f"Op({self.id}-{self.type})"

    def __hash__(self) -> int:
        return hash(self.id)

    @staticmethod
    def ops_by_type(ops: list["Op"]) -> dict[str, list["Op"]]:
        """Generate a map of module types to lists of Op instances."""
        ops_by_type: dict[str, list["Op"]] = {}
        for op in ops:
            if op.type not in ops_by_type:
                ops_by_type[op.type] = []
            ops_by_type[op.type].append(op)
        return ops_by_type

def load_ops_from_dot(filepath: str):
    op_graph = read_dot(filepath)
    op_dict: dict[str, Op] = {}
    mixing_ops: list[str] = []

    # CREATE ALL THE OPERATIONS
    for nid, attrs in op_graph.nodes(data=True):
        label = (attrs.get("label") or "").strip('"')
        if label == "mix":
            op_dict[nid] = Op(nid, type="mix", duration=12)
            mixing_ops.append(nid)
        elif label == "(0,1)":
            op_dict[nid] = Op(nid, type="input-0", duration=6)
        elif label == "(1,1)":
            op_dict[nid] = Op(nid, type="input-1", duration=6)
        else:
            op_dict[nid] = Op(nid, type="other", duration=3)

    # CONNECT PARENTS AND CHILDREN
    for src, dst in op_graph.edges():
        op_dict[src].children.append(op_dict[dst])
        op_dict[dst].parents.append(op_dict[src])

    # ADD WASTE AND OUTPUT NODES FOR MIX OPERATIONS
    for nid in mixing_ops:
        child_count = len(op_dict[nid].children)
        if child_count == 1:
            waste_operation = Op("waste_" + nid, type="waste", duration=1)
            op_dict[waste_operation.id] = waste_operation
            op_dict[nid].children.append(waste_operation)
            waste_operation.parents.append(op_dict[nid])
        elif child_count == 0:
            output_operation = Op("output_" + nid, type="output", duration=1)
            op_dict[output_operation.id] = output_operation
            op_dict[nid].children.append(output_operation)
            output_operation.parents.append(op_dict[nid])
    operations_list = list(op_dict.values())

    return sorted(operations_list, key=lambda o: o.critical_path_length(), reverse=True)
