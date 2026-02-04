import argparse
import numpy as np

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
parser.add_argument("--height", type=int, default=8, help="Height of the OpenDrop board.")
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

encoded_instructions = set[Op]()

protocol = dict[int, set[Position]]()

# Generate frame-based JSON protocol for in-module operations

reservoir_ranges = {
        Position(1,1): (0, 6),
        Position(14,1): (6, 12),
        Position(1,6): (12, 18),
        Position(14,6): (18, 24),
    }

for tick in range(max(op.end_time for op in scheduled_ops) + 1):
    
    active_ops = [op for op in scheduled_ops if op.start_time == tick and op not in encoded_instructions]

    for op in active_ops:
        
        module = modules_by_id[op.module]

        if module.type in (Type.INPUT_0, Type.INPUT_1):
            dispense_frames = get_dispense_frames(module.pos, reservoir_ranges)
            
            # convert binary strings to positions
            for frame in dispense_frames:
                frame_num = int(frame["frame"])
                positions = set[Position]()
                for y in range(args.height):
                    row = str(frame[f"y{y}"])
                    for x in range(args.width):
                        if row[x] == "1":
                            positions.add(Position(x, y))
                protocol_tick = tick + frame_num - 1
                if protocol_tick not in protocol:
                    protocol[protocol_tick] = set()
                protocol[protocol_tick].update(positions)
                encoded_instructions.add(op)
        elif module.type == Type.MIX:
            # For mixing, just activate the module area for the duration
            module_cells = [Position(x, y) for x in range(module.pos.x, module.pos.x + module.width) for y in range(module.pos.y, module.pos.y + module.height)]
            
            module_indices = np.array([[0, 1], [2, 3]], dtype=int)
            for t in range(op.start_time, op.end_time):
                if t not in protocol:
                    protocol[t] = set()
                # Activate cells in clockwise fashion around perimeter of module area
                
                protocol[t].add(module_cells[int(module_indices[0][0])])

                module_indices = np.rot90(module_indices, k=1, axes=(0,1))
            
            
            # After mixing, need to split and move droplets to exits
            

            encoded_instructions.add(op)
        elif module.type in (Type.OUTPUT, Type.WASTE):
            pass
        elif module.type == Type.STORAGE:
            pass

# Add routes in between module end and start times
for child, parent, route in routes:
    start_time = parent.end_time
    for tick in range(len(route.path)):
        protocol[tick].update(route.path[tick - max(child.start_time, parent.end_time)])

# Write protocol to output json
# Format: 
# [{
#  "y0": "111111111111111100",
#  "y1": "111111111111111100",
#  "y2": "111111111111111100",
#  "y3": "111111111111111100",
#  "y4": "111111111111111100",
#  "y5": "111111111111111100",
#  "y6": "111111111111111100",
#  "y7": "111111111111111100",
#  "frame": 1
# }]

with open(args.output_instructions, "w") as f:
    protocol_frames = list[dict[str, str]]()
    for tick in range(max(protocol.keys()) + 1):
        frame_dict: dict[str, str] = {}
        for y in range(args.height):
            row = ["0"] * args.width
            if tick in protocol:
                for pos in protocol[tick]:
                    if pos.y == y:
                        row[pos.x] = "1"
            frame_dict[f"y{y}"] = "".join(row)
        frame_dict["frame"] = tick + 1 # type: ignore
        protocol_frames.append(frame_dict)
    import json
    json.dump(protocol_frames, f, indent=4)