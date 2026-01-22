from api import Op
from networkx.drawing.nx_pydot import read_dot


# LOAD OPERATIONS FROM DOT FILE AND RETURN LIST
def load_ops_from_dot(filepath: str):
    op_graph = read_dot(filepath)
    op_dict: dict[str, Op] = {}
    mixing_ops: list[str] = []

    # CREATE ALL THE OPERATIONS
    for nid, attrs in op_graph.nodes(data=True):
        label = (attrs.get("label") or "").strip('"')
        if label == "mix":
            op_dict[nid] = Op(nid, type="mix", duration=12)
            mixing_ops.append(nid)
        elif label == "(0,1)":
            op_dict[nid] = Op(nid, type="input-zero", duration=6)
        elif label == "(1,1)":
            op_dict[nid] = Op(nid, type="input-one", duration=6)
        else:
            op_dict[nid] = Op(nid, type="other", duration=3)

    # CONNECT PARENTS AND CHILDREN
    for src, dst in op_graph.edges():
        op_dict[src].children.append(op_dict[dst])
        op_dict[dst].parents.append(op_dict[src])

    # ADD WASTE NODES FOR MIX OPERATIONS
    for nid in mixing_ops:
        child_count = len(op_dict[nid].children)
        if child_count == 1:
            waste_operation = Op("waste_" + nid, type="waste", duration=1)
            op_dict[waste_operation.name] = waste_operation
            op_dict[nid].children.append(waste_operation)
            waste_operation.parents.append(op_dict[nid])
    operations_list = list(op_dict.values())

    return sorted(operations_list, key=lambda o: o.critical_path_length(), reverse=True)

def can_schedule(op: Op, tick: int, modules_busy: dict[str, int], available_modules: dict[str, int]) -> bool:
    """Check if an operation can be scheduled at the given tick."""
    
    return True

def list_scheduler(ops: list[Op], available_modules: dict[str, int]) -> list[Op]:
    """Schedules operations based on available modules using a simple list scheduling algorithm."""

    # Initialize scheduling structures
    scheduled_ops = list[Op]()

    unfinished_ops = list[Op]() 
    
    modules_busy = dict.fromkeys(available_modules.keys(), 0)

    # Initial candidate operations: those with all parents as inputs
    candidate_ops = [op for op in ops if all([parent.is_input() for parent in op.parents])]

    tick = 0
    while len(scheduled_ops) < len(ops):        
        # Check if any of the operations running at the current tick are finished
        terminating_ops = list[Op]()
        for op in unfinished_ops:
            if op.end_time == tick:
                # Relinquish module to scheduler
                terminating_ops.append(op)
                modules_busy[op.type] -= 1
        # Remove terminated operations from running list (done in separate loop avoid modifying list while iterating)        
        for op in terminating_ops:
            unfinished_ops.remove(op)
            
        # Sort candidates by critical path length (ascending)
        candidate_ops.sort(key=lambda o: o.critical_path_length(), reverse=False)

        # Identify operations that can be scheduled at this tick
        scheduleable_ops = [op for op in candidate_ops if can_schedule(op, tick, modules_busy, available_modules)]

        for op in scheduleable_ops:
            # Assign module
            modules_busy[op.type] += 1

            # Schedule operation
            op.start_time = tick
            op.end_time = tick + op.duration
            scheduled_ops.append(op)
            unfinished_ops.append(op)

            # Remove from candidate list
            candidate_ops.remove(op)

            for parent in op.parents:
                # If all children of parent are scheduled, add to candidate list
                if parent.is_input():
                    parent.start_time = tick - parent.duration
                    parent.end_time = tick
                    scheduled_ops.append(parent)
                elif (parent.end_time < tick):
                    # Create storage operation, schedule it, and insert between parent and op.
                    pass
            
            for child in op.children:
                if child not in candidate_ops and child.parents_scheduled():
                    candidate_ops.append(child)


        tick += 1

    return scheduled_ops
