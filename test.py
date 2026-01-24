import json
from api import Holder, Module, Position


from scheduler import load_ops_from_dot as load_graph, list_scheduler as scheduler
from placer import left_edge_bind_modules as placer
from router import route as router

def test_position():
    pos1 = Position(3, 5)
    pos2 = Position(3, 5)
    pos3 = Position(4, 5)

    assert pos1 == pos2, "Position equality failed"
    assert pos1 != pos3, "Position inequality failed"
    assert hash(pos1) == hash(pos2), "Position hashing failed"

def test_scheduler():
    AVAILABLE_MODULES = {"mix": 1, "input-zero": 1, "input-one": 1, "output": 1, "storage": 2, "waste": 1}
    
    print("Testing scheduler with smallgraph.dot...")
    ops = load_graph("smallgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("---")

    print("Testing scheduler with mediumgraph.dot...")
    ops = load_graph("mediumgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("---")
    
    print("Testing scheduler with largegraph.dot...")
    ops = load_graph("largegraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("---")

def test_binder():
    
    AVAILABLE_MODULES = {"mix": 1, "input-zero": 1, "input-one": 1, "output": 1, "storage": 2, "waste": 1}
    print("Testing binder with smallgraph.dot...")
    ops = load_graph("smallgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("Binding modules...")
    modules_list: list[Module] = []
    
    with open("modules.json", "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:
            modules_list.append(
                Module(
                    pos=mod["pos"],
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

    placer(schedule, modules_list, list(AVAILABLE_MODULES.keys()))

    for op in schedule:
        print(op)
    print("---")
    

def test_router():

    AVAILABLE_MODULES = {"mix": 1, "input-zero": 1, "input-one": 1, "output": 1, "storage": 2, "waste": 1}
    print("Testing binder with smallgraph.dot...")
    ops = load_graph("smallgraph.dot")
    schedule = scheduler(ops, AVAILABLE_MODULES)
    for op in schedule:
        print(op)
    print("Binding modules...")
    modules_list: list[Module] = []
    
    with open("modules.json", "r") as f:
        topology = json.load(f)

        for mod in topology["modules"]:
            modules_list.append(
                Module(
                    pos=Position(*mod["pos"]),
                    id=mod["id"],
                    type=mod["type"],
                    entrance=Position(*mod["entrance"]),
                    storage=Holder(capacity=mod["storage"]),
                    exit=Position(*mod["exit"]),
                    width=mod.get("width", 3),
                    height=mod.get("height", 3),
                    pad=mod.get("pad", 1)
                )
            )

    placer(schedule, modules_list, list(AVAILABLE_MODULES.keys()))

    mods_by_id = {mod.id: mod for mod in modules_list}
    print(mods_by_id)
    print("Routing droplets...")
    
    routes = router(schedule, mods_by_id)
    for op_id, route in routes: 
        print(f"Operation {op_id} route: {route}")
    print("---")

if __name__ == "__main__":
    test_position()
    # test_scheduler()
    # test_binder()
    test_router()