import argparse

from api.module import Module, load_modules
from api.op import Op, load_ops_from_dot as load_graph
from api.util import Type, Position, get_dispense_frames

from scheduler import list_scheduler as schedule
from placer import left_edge_bind_modules as placer
from router import route as router

parser = argparse.ArgumentParser(
    description="Translate dot graph to OpenDrop instructions."
)
parser.add_argument(
    "input_dot",
    type=str,
    help="Path to input dot file representing the operation graph.",
)
parser.add_argument(
    "output_instructions",
    type=str,
    help="Path to output file for OpenDrop instructions.",
)
parser.add_argument(
    "--module_topology",
    type=str,
    help="Path to JSON file specifying module locations and sizes.",
)
parser.add_argument(
    "--max_droplets", type=int, help="Maximum number of droplets to use."
)
parser.add_argument(
    "--height", type=int, default=8, help="Height of the OpenDrop board."
)
parser.add_argument(
    "--width", type=int, default=16, help="Width of the OpenDrop board."
)
parser.add_argument(
    "--heaters", type=int, default=3, help="Number of heating modules available."
)
parser.add_argument(
    "--mixers", type=int, default=2, help="Max number of mixing modules to use."
)
parser.add_argument(
    "--storages", type=int, default=3, help="Max number of storage units to use."
)
parser.add_argument(
    "--inputs", type=int, default=2, help="Number of input modules available."
)
parser.add_argument(
    "--outputs", type=int, default=1, help="Number of output modules available."
)
parser.add_argument(
    "--wastes", type=int, default=1, help="Number of waste modules available."
)


args = parser.parse_args()

BOARD_DIMENSIONS = (args.width, args.height)

num_inputs: int = args.inputs

modules_list: list[Module] = []
if args.module_topology:
    modules_list = load_modules(args.module_topology)

modules_by_id = {mod.id: mod for mod in modules_list}

max_droplets: int | None = args.max_droplets

mixers: int = int(args.mixers)
outputs: int = int(args.outputs)
storages: int = int(args.storages)
wastes: int = int(args.wastes)

AVAILABLE_MODULES: dict[Type, int] = {
    Type.MIX: mixers,
    Type.INPUT_0: num_inputs,
    Type.INPUT_1: num_inputs,
    Type.OUTPUT: outputs,
    Type.STORAGE: storages,
    Type.WASTE: wastes,
}
scheduled_ops = schedule(load_graph(args.input_dot), AVAILABLE_MODULES, max_droplets)

placer(scheduled_ops, modules_list, list(AVAILABLE_MODULES.keys()))

routes = router(scheduled_ops, modules_by_id)

# Generate frame-based JSON protocol for in-module operations

reservoir_ranges = {
    Position(1, 1): (0, 6),
    Position(14, 1): (6, 12),
    Position(1, 6): (12, 18),
    Position(14, 6): (18, 24),
}

# Determine initial simulation horizon from scheduled operations
max_tick = 0
if scheduled_ops:
    max_tick = max(op.end_time for op in scheduled_ops)

protocol = [set[Position]() for _ in range(max_tick + 1)]

# Build helper mapping from parent ops to their outgoing routes (child_op, route)
routes_by_parent: dict[Op, list[tuple[Op, object]]] = {}
for child_op, parent_op, rt in routes:
    if parent_op not in routes_by_parent:
        routes_by_parent[parent_op] = []
    routes_by_parent[parent_op].append((child_op, rt))


# Phase 1: add in-module operation frames (inputs and mixing)
for op in scheduled_ops:
    module = modules_by_id[op.module]

    # Input operations: play 6-frame dispense animation starting at op.start_time
    if module.type in (Type.INPUT_0, Type.INPUT_1):
        dispense_frames = get_dispense_frames(module.pos, reservoir_ranges)

        for idx, frame in enumerate(dispense_frames):
            protocol_tick = op.start_time + idx

            # Convert frame rows to active positions, respecting current board size
            for y in range(args.height):
                row_key = f"y{y}"
                if row_key not in frame:
                    continue
                row_str = str(frame[row_key])
                for x in range(min(args.width, len(row_str))):
                    if row_str[x] == "1":
                        protocol[protocol_tick].add(Position(x, y))

            if protocol_tick > max_tick:
                max_tick = protocol_tick

    # Mixing operations: clockwise rotation plus final split frames to route exits
    elif module.type == Type.MIX:
        cycle = mixer_cycle_positions(module)
        cycle_len = len(cycle)

        # Reserve the last tick of the op for splitting towards exit ports (if any)
        split_tick = max(op.start_time, op.end_time - 1)

        # Core rotation: from start_time up to (but not including) split_tick
        for t in range(op.start_time, split_tick):
            idx = (t - op.start_time) % cycle_len
            pos = cycle[idx]
            protocol[t].add(pos)
            if t > max_tick:
                max_tick = t

        # Splitting: activate exit ports corresponding to routes from this mix op
        outgoing = routes_by_parent.get(op, [])
        if outgoing:
            for child_op, rt in outgoing:
                # Route src is the chosen port position on this module
                src_pos = getattr(rt, "src", None)
                if isinstance(src_pos, Position):
                    protocol[split_tick].add(src_pos)
            if split_tick > max_tick:
                max_tick = split_tick


# Phase 2: add routes between operations
# routes contains tuples (child_op, parent_op, route)
for child_op, parent_op, rt in routes:
    route_start_tick = parent_op.end_time

    for step_index, pos in enumerate(getattr(rt, "path", [])):
        tick = route_start_tick + step_index

        protocol[tick].add(pos)
        if tick > max_tick:
            max_tick = tick


# Phase 3: write protocol to JSON frames
import json

with open(args.output_instructions, "w") as f:
    protocol_frames: list[dict[str, str | int]] = []
    for tick in range(max_tick + 1):
        frame_dict: dict[str, str | int] = {}
        for y in range(args.height):
            row = ["0"] * args.width
            if tick in protocol:
                for pos in protocol[tick]:
                    if (
                        0 <= pos.x < args.width
                        and 0 <= pos.y < args.height
                        and pos.y == y
                    ):
                        row[pos.x] = "1"
            frame_dict[f"y{y}"] = "".join(row)
        frame_dict["frame"] = tick + 1
        protocol_frames.append(frame_dict)

    json.dump(protocol_frames, f, indent=4)
