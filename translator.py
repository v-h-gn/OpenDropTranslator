import argparse

from api.module import Module, load_modules
from api.op import load_ops_from_dot as load_graph
from api.util import Type

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

for op, parent, route in routes:
    print(f"Route from {parent} to {op}:")
    route.print_route(
        board_size=BOARD_DIMENSIONS,
        no_go_cells=set(),
        modules=modules_list,
    )
    print("\n")