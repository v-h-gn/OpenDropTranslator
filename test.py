from api.module import Module, load_modules
from api.op import load_ops_from_dot as load_graph
from api.util import Position, Type


from scheduler import list_scheduler as scheduler
from placer import left_edge_bind_modules as placer
from router import route as router

AVAILABLE_MODULES = {
        Type.MIX: 1,
        Type.INPUT_0: 1,
        Type.INPUT_1: 1,
        Type.OUTPUT: 1,
        Type.STORAGE: 2,
        Type.WASTE: 1,
}

def test_position():
    pos1 = Position(3, 5)
    pos2 = Position(3, 5)
    pos3 = Position(4, 5)

    assert pos1 == pos2, "Position equality failed"
    assert pos1 != pos3, "Position inequality failed"
    assert hash(pos1) == hash(pos2), "Position hashing failed"


def test_scheduler():

    print("Testing scheduler with smallgraph.dot...")
    ops = load_graph("example_protocols/smallgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("---")

    print("Testing scheduler with mediumgraph.dot...")
    ops = load_graph("example_protocols/mediumgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("---")

    print("Testing scheduler with largegraph.dot...")
    ops = load_graph("example_protocols/largegraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("--- ENDING SCHEDULER TEST ---")


def test_binder():
    print("Testing binder with smallgraph.dot...")
    ops = load_graph("example_protocols/smallgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("Binding modules...")
    modules_list: list[Module] = load_modules("modules.json")

    placer(schedule, modules_list, list(AVAILABLE_MODULES.keys()))
    for op in schedule:
        print(op)

    print("---")   

    print("Testing binder with mediumgraph.dot...")
    ops = load_graph("example_protocols/mediumgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("Binding modules...")
    modules_list: list[Module] = load_modules("modules.json")

    placer(schedule, modules_list, list(AVAILABLE_MODULES.keys()))

    for op in schedule:
        print(op)
    print("---")


    print("Testing binder with largegraph.dot...")
    ops = load_graph("example_protocols/largegraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("Binding modules...")
    modules_list: list[Module] = load_modules("modules.json")
    placer(schedule, modules_list, list(AVAILABLE_MODULES.keys()))
    for op in schedule:
        print(op)
    print("--- ENDING BINDER TEST ---")


def test_router():

    print("Testing router with largegraph.dot...")
    ops = load_graph("example_protocols/largegraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)

    print("Binding modules...")
    modules_list: list[Module] = load_modules("modules.json")

    placer(schedule, modules_list, list(AVAILABLE_MODULES.keys()))

    mods_by_id = {mod.id: mod for mod in modules_list}
    print(mods_by_id)
    for op in schedule:
        print(op)
    print("Routing droplets...")

    routes = router(schedule, mods_by_id)
    for op1, op2, route in routes:
        print(f"Route from {op1.id} of type {op1.type} to {op2.id} of type {op2.type}:")
        route.print_route(modules=modules_list)
    print("--- ENDING ROUTER TEST ---")

if __name__ == "__main__":
    test_position()
    #test_scheduler()
    #test_binder()
    test_router()
