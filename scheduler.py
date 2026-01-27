from api.op import InputOp, Op, StorageOp, WasteOp, OutputOp

from api.util import Type

def can_schedule(
    op: Op,
    tick: int,
    modules_busy: dict[Type, int],
    available_modules: dict[Type, int],
    current_droplets: int,
    max_droplets: int,
) -> bool:
    """Check if an operation can be scheduled at the given tick."""

    # Check if parents of op which are inputs have available modules
    dispense_parents = [p for p in op.parents if isinstance(p, InputOp)]
    non_dispense_parents = [p for p in op.parents if not isinstance(p, InputOp)]

    parent_modules_available = all(
        modules_busy.get(p.type, 0) < available_modules.get(p.type, 0)
        for p in dispense_parents
    )

    # Check if non-dispense parents have completed by this tick
    non_dispense_parents_scheduled = all(
        p.end_time <= tick for p in non_dispense_parents
    )

    # Check if op's required module is available
    op_module_available = modules_busy.get(op.type, 0) < available_modules.get(
        op.type, 0
    )

    # Check if scheduling this op would exceed max droplets
    new_droplets = current_droplets + len(dispense_parents)

    return (
        parent_modules_available
        and non_dispense_parents_scheduled
        and op_module_available
        and (new_droplets <= max_droplets)
    )


def list_scheduler(
    ops: list[Op], available_modules: dict[Type, int], max_droplets: int | None = None
) -> list[Op]:
    """Schedules operations based on available modules using a simple list scheduling algorithm."""

    max_droplets = (
        max_droplets if max_droplets is not None else sum(available_modules.values())
    )

    current_droplets = 0

    # Initialize scheduling structures
    scheduled_ops = list[Op]()

    unfinished_ops = list[Op]()

    modules_busy = dict.fromkeys(available_modules.keys(), 0)

    # Initial candidate operations: those with all parents as inputs
    candidate_ops = [
        op
        for op in ops
        if op.parents and all([isinstance(parent, InputOp) for parent in op.parents])
    ]

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
        scheduleable_ops = [
            op
            for op in candidate_ops
            if can_schedule(
                op,
                tick,
                modules_busy,
                available_modules,
                current_droplets,
                max_droplets,
            )
        ]

        for op in scheduleable_ops:
            # Assign module
            modules_busy[op.type] += 1

            if isinstance(op, OutputOp):
                current_droplets -= 1

            if isinstance(op, WasteOp):
                current_droplets -= 1

            # Schedule operation
            op.start_time = tick
            op.end_time = tick + op.duration
            scheduled_ops.append(op)
            unfinished_ops.append(op)

            # Remove from candidate list
            candidate_ops.remove(op)

            for parent in op.parents:
                # If all children of parent are scheduled, add to candidate list
                if isinstance(parent, InputOp):
                    current_droplets += 1
                    parent.start_time = tick - parent.duration
                    parent.end_time = tick
                    scheduled_ops.append(parent)
                elif parent.end_time < tick:
                    # Create storage operation, schedule it, and insert between parent and op.
                    storage_op = StorageOp(
                        id=f"storage_{parent.id}_to_{op.id}",
                        duration=1,
                    )
                    storage_op.start_time=parent.end_time
                    storage_op.end_time=parent.end_time + 1
                    storage_op.parents=[parent]
                    storage_op.children=[op]
                    
                    parent.children.remove(op)
                    parent.children.append(storage_op)
                    op.parents.remove(parent)
                    op.parents.append(storage_op)
                    scheduled_ops.append(storage_op)
                    ops.append(storage_op)
                    modules_busy[Type.STORAGE] += 1

            for child in op.children:
                child_not_candidate = child not in candidate_ops
                child_parents_scheduled = child.parents_scheduled(
                    excluding=lambda p: isinstance(p, InputOp)
                )
                if child_not_candidate and child_parents_scheduled:
                    candidate_ops.append(child)

        tick += 1

    # offset negative start times to start at zero
    start_offset = 0 - min(op.start_time for op in scheduled_ops)

    for op in scheduled_ops:
        op.start_time += start_offset
        op.end_time += start_offset

    return sorted(scheduled_ops, key=lambda o: o.start_time)
