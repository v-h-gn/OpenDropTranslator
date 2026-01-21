from api import Op
from networkx.drawing.nx_pydot import read_dot


# LOAD OPERATIONS FROM DOT FILE AND RETURN LIST
def load_ops_from_dot(filepath: str):
    op_graph = read_dot(filepath)
    op_dict = dict[str, Op]()
    mixing_ops = list[str]()

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

    return sorted(operations_list, key=lambda o: o.name, reverse=True)


# THE MAIN SCHEDULER FUNCTION - ASSIGNS START AND END TIMES
def list_scheduler(ops: list[Op], available_modules: dict[str, int]) -> list[Op]:
    tick = 0
    scheduled_ops = list[Op]()
    running_ops = list[Op]()  # OPERATIONS CURRENTLY EXECUTING
    modules_busy = dict[str, int]()
    for module_type in available_modules.keys():
        modules_busy[module_type] = 0

    # KEEP GOING UNTIL ALL OPERATIONS ARE DONE
    for tick in range(100):
        # CHECK IF ANY RUNNING OPERATIONS FINISHED
        terminating_ops = list[Op]()
        for op in running_ops:
            if op.end == tick:
                # print(f"Operation {op.name}-({op.type}) finished at time {tick}")
                terminating_ops.append(op)
        # REMOVE FINISHED OPERATIONS FROM RUNNING LIST
        for op in terminating_ops:
            running_ops.remove(op)
            modules_busy[op.type] -= 1

        # FIND OPERATIONS THAT ARE READY TO SCHEDULE
        scheduleable_ops = list[Op]()
        for op in ops:
            # CHECK IF NOT SCHEDULED AND PARENTS DONE
            if op.start == -1 and op.parents_done(tick):
                # print(f"Operation {op.name}-({op.type}) is ready to schedule at time {tick}")
                scheduleable_ops.append(op)

        # SCHEDULE READY OPERATIONS
        for op in scheduleable_ops:
            # print(f"Trying to schedule operation {op.name}-({op.type}) at time {tick}")
            # print(f"Modules busy for {op.type}: {modules_busy[op.type]}, Available: {available_modules[op.type]}")
            if modules_busy[op.type] < available_modules[op.type]:
                modules_busy[op.type] += 1
                op.start = tick
                op.end = tick + op.duration
                op.module = f"{op.type}-{modules_busy[op.type]-1}"
                running_ops.append(op)
                scheduled_ops.append(op)
                # print(f"Scheduled operation {op.name}-({op.type}) from time {op.start} to {op.end} on module {op.module}")

        if ops == sorted(scheduled_ops, key=lambda o: o.name, reverse=True):
            break

    return scheduled_ops
