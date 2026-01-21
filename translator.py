import argparse
import json

from scheduler import load_ops_from_dot as load_from_dot, list_scheduler as schedule
parser = argparse.ArgumentParser(description="Translate dot graph to OpenDrop instructions.")
parser.add_argument("input_dot", type=str, help="Path to input dot file representing the operation graph.")
parser.add_argument("output_instructions", type=str, help="Path to output file for OpenDrop instructions.")
parser.add_argument("--module_topology", type=str, help="Path to JSON file specifying module locations and sizes.")
parser.add_argument("--width", type=int, default=6, help="Width of the OpenDrop board.")
parser.add_argument("--height", type=int, default=14, help="Height of the OpenDrop board.")
parser.add_argument("--heaters", type=int, default=3, help="Number of heating modules available.")
parser.add_argument("--mixers", type=int, default=2, help="Max number of mixing modules to use.")
parser.add_argument("--storages", type=int, default=3, help="Max number of storage units to use.")
parser.add_argument("--inputs", type=int, default=2, help="Number of input modules available.")
parser.add_argument("--outputs", type=int, default=1, help="Number of output modules available.")
parser.add_argument("--wastes", type=int, default=1, help="Number of waste modules available.")


args = parser.parse_args()

BOARD_DIMENSIONS = (args.height, args.width)

# WASTE LOCATION ON RIGHT SIDE OF CHIP
WASTE_RESERVOIR = (args.height - 1, 2)

num_inputs: int = args.inputs

BINDABLE_MODULES = ["mix", "heat", "detect"]

AVAILABLE_MODULES = {
    "mix": args.mixers,
    "heat": args.heaters,
    "storage": args.storages,
    "output": args.outputs,
    "waste": args.wastes,
}
for i in range(num_inputs):
    AVAILABLE_MODULES[f"input-{i}"] = 1

scheduled_ops = schedule(load_from_dot(args.input_dot), AVAILABLE_MODULES)

if args.module_topology:
    with open(args.module_topology, "r") as f:
        topology = json.load(f)

        
