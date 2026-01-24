from api import Module

from scheduler import load_ops_from_dot as load_graph, list_scheduler as scheduler

from binder import left_edge_bind_modules as placer
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
    
    
    modules: list[Module] = []

    placer(schedule, modules, list(AVAILABLE_MODULES.keys()))

    

def test_router():
    pass

if __name__ == "__main__":
    test_scheduler()
    test_binder()
    test_router()