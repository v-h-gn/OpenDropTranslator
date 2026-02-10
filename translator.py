import argparse

from pyparsing import cast

from api.module import Module, load_modules
from api.op import Op, MixOp, load_ops_from_dot as load_graph
from api.util import Type, Position, get_dispense_frames
from api.route import Route

from scheduler import list_scheduler as schedule
from placer import left_edge_bind_modules as placer
from router import route as router, path_find as path

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
max_tick = max(op.end_time for op in scheduled_ops)

protocol = [set[Position]() for _ in range(max_tick + 1)]
combined_routes = [[set[Position]() for _ in range(BOARD_DIMENSIONS[0] * BOARD_DIMENSIONS[1])] for _ in range(len(scheduled_ops))]

# Build helper mapping from parent ops to their outgoing routes (child_op, route)
routes_by_parent: dict[Op, list[tuple[Op, Route]]] = {}
for child_op, parent_op, rt in routes:
    if parent_op not in routes_by_parent:
        routes_by_parent[parent_op] = []
    routes_by_parent[parent_op].append((child_op, rt))

# Build helper mapping from child ops to their incoming routes (parent_op, route)
routes_by_child: dict[Op, list[tuple[Op, Route]]] = {}
for child_op, parent_op, rt in routes:
    if child_op not in routes_by_child:
        routes_by_child[child_op] = []
    routes_by_child[child_op].append((parent_op, rt))

# Phase 1: add in-module operation frames (inputs and mixing)
for op_num, op in enumerate(scheduled_ops):
    module = modules_by_id[op.module]

    incoming_routes = routes_by_child.get(op, [])
    outgoing_routes = routes_by_parent.get(op, [])

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

    # Mixing operations: clockwise rotation plus final split frames to route exits
    elif module.type == Type.MIX:
        # Get droplet entry positions from incoming routes
        entries = [route.dst for _, route in incoming_routes]
        
        # Route droplet from entrance to internal mixing area
        internals = list[Route]()
        for entry in entries:
            internals.append(path(entry, module.get_nearest_internal_pos(entry), module.get_padding_cells(), BOARD_DIMENSIONS))
        entry_ticks = max(len(r.path) for r in internals)

        for internal_route in internals:
            for tick, pos in enumerate(internal_route.path):
                protocol[op.start_time + tick].add(pos)

        # Combine route paths into single set of positions for entry phase
        path_length = max(len(r.path) for _, r in incoming_routes)
        

        mix_op = cast(MixOp, op)
        split_tick = mix_op.split_tick  # Last tick is for splitting
        # Core rotation: from start_time up to (but not including) split_tick
        for tick in range(op.start_time, op.start_time + split_tick):
            idx = (tick - (op.start_time + entry_ticks))
            pos = mix_op.animation(module.pos, idx)
            protocol[tick].update(pos)

        # Splitting: activate exit ports corresponding to routes from this mix op
        exits = [route.src for _, route in outgoing_routes]
        externals = list[Route]()
        for exit_pos in exits:
            externals.append(path(module.get_nearest_internal_pos(exit_pos), exit_pos, set(), BOARD_DIMENSIONS))
        
        for external_route in externals:
            for tick, pos in enumerate(external_route.path):
                protocol[op.start_time + split_tick + tick].add(pos)

    elif module.type == Type.STORAGE:
        # Storage operations: hold droplet in place for duration
        for t in range(op.start_time, op.end_time):
            protocol[t].add(module.pos)

    elif module.type == Type.OUTPUT or module.type == Type.WASTE:
        # Output/Waste operations: hold droplet in place for duration
        for t in range(op.start_time, op.end_time):
            protocol[t].add(module.pos)

# Phase 3: write protocol to JSON frames
import json

with open(args.output_instructions, "w") as f:
    protocol_frames: list[dict[str, str | int]] = []
    max_tick = len(protocol) 
    for tick in range(max_tick):
        frame_dict: dict[str, str | int] = {}
        for y in range(args.height):
            row = ["0"] * args.width
            for pos in protocol[tick]:
                if pos.y == y:
                    row[pos.x] = "1"
            frame_dict[f"y{y}"] = "".join(row)
        frame_dict["frame"] = tick + 1
        protocol_frames.append(frame_dict)

    json.dump(protocol_frames, f, indent=4)
