import argparse


from api.op import load_ops_from_dot as load_graph
from api.module import Module, load_modules
from api.util import Type, Position

from scheduler import list_scheduler as schedule
from placer import left_edge_bind_modules as placer
from router import route as router, convert_to_protocol

parser = argparse.ArgumentParser(
    description="Translate dot graph to OpenDrop instructions."
)
parser.add_argument(
    "--input",
    type=str,
    default="example_protocols/mediumgraph.dot",
    help="Path to input dot file representing the operation graph.",
)
parser.add_argument(
    "--output",
    type=str,
    default="protocol.json",
    help="Path to output file for OpenDrop instructions.",
)
parser.add_argument(
    "--module_topology",
    type=str,
    default="modules.json",
    help="Path to JSON file specifying module locations and sizes.",
)
parser.add_argument(
    "--max_droplets", type=int, default=100, help="Maximum number of droplets to use."
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
scheduled_ops = schedule(load_graph(args.input), AVAILABLE_MODULES, max_droplets)

placer(scheduled_ops, modules_list, list(AVAILABLE_MODULES.keys()))

routes = router(scheduled_ops, modules_list)

# Generate frame-based JSON protocol for in-module operations

# Determine initial simulation horizon from scheduled operations
max_tick = max(op.end_time for op in scheduled_ops)

protocol = [set[Position]() for _ in range(max_tick + 1)]

protocol = convert_to_protocol(scheduled_ops, modules_list, routes)

# Phase 3: write protocol to JSON frames
import json

with open(args.output, "w") as f:
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
