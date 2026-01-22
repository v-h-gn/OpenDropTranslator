import argparse
import json

from api import Module, Holder

from scheduler import load_ops_from_dot as load_from_dot, list_scheduler as schedule


parser = argparse.ArgumentParser(description="Translate dot graph to OpenDrop instructions.")
parser.add_argument("input_dot", type=str, help="Path to input dot file representing the operation graph.")
parser.add_argument("output_instructions", type=str, help="Path to output file for OpenDrop instructions.")
parser.add_argument("--module_topology", type=str, help="Path to JSON file specifying module locations and sizes.")
parser.add_argument("--max_droplets", type=int, help="Maximum number of droplets to use.")
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

modules_list: list[Module] = []
if args.module_topology:
    with open(args.module_topology, "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:
            modules_list.append(
                Module(
                    pos=mod["position"],
                    id=mod["id"],
                    type=mod["type"],
                    entrance=mod["entrance"],
                    storage=Holder(capacity=mod["storage"]),
                    exit=mod["exit"],
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1)
                )
            )

max_droplets: int | None = args.max_droplets

mixers: int = int(args.mixers)
outputs: int = int(args.outputs)
storages: int = int(args.storages)
wastes: int = int(args.wastes)

AVAILABLE_MODULES: dict[str, int] = {
    "mix": mixers,
    "input-zero": num_inputs,
    "input-one": num_inputs,
    "output": outputs,
    "storage": storages,
    "waste": wastes,
}
scheduled_ops = schedule(load_from_dot(args.input_dot), AVAILABLE_MODULES, max_droplets)
