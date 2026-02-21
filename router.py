from api.util import Position, Type, path_find
from api.op import Op
from api.module import Module, Port
from api.route import Route

irv = Position.irv


def get_parent_occupied_cells(op: Op, occupied_cells: dict[Op, set[Position]]) -> set[Position]:
    """Get occupied cells for all parent operations of the given operation."""
    occupied = set[Position]()
    for parent in op.parents:
        parent_mod = parent.module
        for x in range(
            parent_mod.pos.x - parent_mod.pad,
            parent_mod.pos.x + parent_mod.width + parent_mod.pad,
        ):
            for y in range(
                parent_mod.pos.y - parent_mod.pad,
                parent_mod.pos.y + parent_mod.height + parent_mod.pad,
            ):
                if parent in occupied_cells:
                    occupied.update(occupied_cells[parent])
                else:
                    occupied.add(Position(x, y))
    return occupied


def get_no_go_cells(ops: list[Op], mods: list[Module]) -> dict[Op, set[Position]]:
    """
    Get all no-go cells on the board at a given tick for the provided operations and modules.
    """
    no_go_cells_by_op: dict[Op, set[Position]] = {}
    for op in ops:
        no_go_cells = set[Position]()
        # Add all module occupied cells
        for other_mod in mods:
            for x in range(
                other_mod.pos.x - other_mod.pad,
                other_mod.pos.x + other_mod.width + other_mod.pad,
            ):
                for y in range(
                    other_mod.pos.y - other_mod.pad,
                    other_mod.pos.y + other_mod.height + other_mod.pad,
                ):
                    no_go_cells.add(Position(x, y))
        own_mod = op.module
        for x in range(own_mod.pos.x - own_mod.pad, own_mod.pos.x + own_mod.width + own_mod.pad):
            for y in range(
                own_mod.pos.y - own_mod.pad,
                own_mod.pos.y + own_mod.height + own_mod.pad,
            ):
                pos = Position(x, y)
                if not own_mod.is_internal(pos):
                    no_go_cells.remove(pos)

        no_go_cells_by_op[op] = no_go_cells

    return no_go_cells_by_op


def get_routes(ops: list[Op], mods: list[Module], tick: int, routed_ops: set[Op]) -> list[tuple[Op, Op, Route]]:
    """Get routes for all operations active at the given tick."""

    routes = list[tuple[Op, Op, Route]]()

    # Identify operations active at the current tick
    active_ops = [op for op in ops if op.start_time <= tick < op.end_time and op not in routed_ops]
    #print(f"Active operations at tick {tick}: {[op.id for op in active_ops]}")
    active_mods = [op.module for op in active_ops]
    occupied_cells: dict[Op, set[Position]] = get_no_go_cells(active_ops, active_mods)

    # Combine all occupied cells into a single set
    occupied = set[Position]()
    for cells in occupied_cells.values():
        occupied.update(cells)

    # Print summary before routing
    #print(f"Tick {tick}: Attempting to route {len(active_ops)} active operations.")
    # for op in active_ops:
        #print(f"Op {op.id} on module {op.module} from {op.start_time} to {op.end_time}")

    # Find routes for each active operation
    for op in active_ops:
        mod = op.module

        # If already routed, skip
        if op in routed_ops:
            # print(f"Skipping routing for {op.id} as it has already been routed.")
            continue

        # Route from each parent to this operation
        for parent in op.parents:
            parent_mod = parent.module

            # If parent and child are on the same module, skip routing
            if parent_mod == mod:
                #print(f"Skipping routing from {parent.id} to {op.id} as both are on the same module {mod.id}.")
                continue

            src, dst = parent_mod.get_nearest_ports(tick, mod)

            parent_mod.used_ports[src][parent.end_time] = Port.EXIT
            mod.used_ports[dst][op.start_time] = Port.ENTRANCE
            # Remove src and dst from occupied cells to allow routing to/from these points
            try:
                route = Route(
                    src,
                    dst,
                    path_find(
                        src=src,
                        dst=dst,
                        no_go_cells=occupied_cells[op] - {src} - {dst},
                        board_size=(16, 8),
                    ),
                )
                routes.append((op, parent, route))
                # print(f"Successfully routed from {parent.id} of type {parent.type} to {op.id} of type {op.type}")
                routed_ops.add(op)
            except RuntimeError as e:
                print(f"Failed to route from {parent.id} to {op.id}: {e}")
                print(f"Parent module: {parent_mod} at {src}, Child module: {mod} at {dst}")
                raise e

    return routes


def all_cycle_IRV(route: Route, compact_route: Route, cycle: int) -> bool:
    """Check for Interference Region Violation (IRV) at a specific cycle between two routes."""
    r_pos = route.path[cycle]
    cr_pos = compact_route.path[cycle]
    r_pos_prev = route.path[cycle - 1] if cycle - 1 >= 0 else None
    cr_pos_prev = compact_route.path[cycle - 1] if cycle - 1 >= 0 else None
    r_pos_next = route.path[cycle + 1] if cycle + 1 < len(route.path) else None
    cr_pos_next = compact_route.path[cycle + 1] if cycle + 1 < len(compact_route.path) else None

    return (
        irv(r_pos, cr_pos_prev)
        or irv(r_pos, cr_pos_next)
        or irv(r_pos_prev, cr_pos)
        or irv(r_pos_next, cr_pos)
        or irv(r_pos, cr_pos)
        or irv(r_pos_prev, cr_pos_prev)
    )


def compact_routes(routes: list[tuple[Op, Op, Route]]) -> None:
    """Parallelize sequential routes while respecting interference regions, adding stalls if necessary."""
    compacted_routes = list[Route]()
    for _, _, route in routes:
        route_must_stall = False
        cycle = 0
        # print(f"Compacting route from {route.src} to {route.dst} with initial length {len(route.path)}")
        # print_route(route)
        while cycle < len(route.path):
            # Check for interference with other routes
            for other_route in compacted_routes:
                # print(f"Checking interference with route from {other_route.src} to {other_route.dst}")
                # print_route(other_route)
                if cycle < len(other_route.path):
                    if all_cycle_IRV(route, other_route, cycle):
                        route_must_stall = True
                        break

            if route_must_stall:
                # Insert a stall by repeating the current position
                route.stall(cycle - 2)
                route_must_stall = False
            else:
                cycle += 1
        compacted_routes.append(route)


def route(ops: list[Op], mods: list[Module]) -> list[tuple[Op, Op, Route]]:
    """Routes droplets between operations based on their module assignments."""

    results = list[tuple[Op, Op, Route]]()

    # Ensure ops are sorted by start time
    ops_sorted: list[Op] = sorted(ops, key=lambda o: o.start_time)

    routed_ops = set[Op]()

    tick = 0
    while ops_sorted:
        ops_and_routes = get_routes(ops_sorted, mods, tick, routed_ops=routed_ops)

        compact_routes(ops_and_routes)

        results.extend(ops_and_routes)
        routed_ops.update([r[1] for r in ops_and_routes])
        routed_ops.update([r[0] for r in ops_and_routes])

        tick += 1
        for op in ops_sorted[:]:
            if op.end_time <= tick:
                ops_sorted.remove(op)

    return results


def convert_to_protocol(ops: list[Op], mods: list[Module], routes: list[tuple[Op, Op, Route]]) -> list[set[Position]]:
    """Convert scheduled operations and routes to a frame-based protocol."""

    max_tick = max(op.end_time for op in ops)

    protocol = [set[Position]() for _ in range(max_tick + 1)]

    i = 0

    while i <= max_tick:
        # For each tick, determine which operations are active and which routes are active
        active_ops = [op for op in ops if op.start_time <= i < op.end_time]
        print(f"Tick {i}: Active operations: {[op.id for op in active_ops]}")
        active_routes = [route for route in routes if route[1].end_time <= i < route[1].end_time + len(route[2].path)]
        print(f"Tick {i}: Active routes: [" + ", ".join(f"{r[1].id}->{r[0].id}" for r in active_routes) + "]")
        for child, parent, route in active_routes:
            droplet_arrival = parent.end_time + len(route.path)
            difference = droplet_arrival - child.start_time
            old_start = child.start_time

            #print(f"Droplet from {parent.id}-{parent.type} to {child.id}-{child.type} arrives at t={droplet_arrival}, child starts at {child.start_time}, difference is {difference}")
            # If the child operation starts before the droplet arrives
            if old_start < droplet_arrival:
                #print(f"Must delay all operations starting at or after {child.start_time} by {difference}.")

                for op in ops:
                    if op.start_time >= old_start:
                        #print(f"Delaying operation {op.id} from {op.start_time}-{op.end_time} to {op.start_time + difference}-{op.end_time + difference}")
                        op.delay(difference, propagate=False)

                for mod in mods:
                    # print(f"Delaying module {mod.id} by {difference} ticks.")
                    for _, port_list in mod.used_ports.items():
                        # Insert UNUSED ports at the position where delayed operations start
                        # This shifts all port statuses for delayed operations forward by 'difference'
                        for _ in range(difference):
                            port_list.insert(old_start, Port.UNUSED)

                # After delaying operations and shifting port lists, we need to remark all ports
                # that correspond to the routes. The issue: when we insert UNUSED at old_start,
                # we shift ALL port markings at position >= old_start forward by 'difference'.
                # But operations with start_time < old_start are NOT delayed, yet their EXIT ports
                # (which might be at position >= old_start) DO get shifted, creating a mismatch.
                # Solution: Clear all port markings and remark them at the correct positions.
                #print(f"Remarking ports for all routes after delay to ensure consistency...")
                
                # First, clear all EXIT and ENTRANCE markings
                for mod in mods:
                    for port in mod.ports:
                        for tick_idx in range(len(mod.used_ports[port])):
                            if mod.used_ports[port][tick_idx] in (Port.EXIT, Port.ENTRANCE):
                                mod.used_ports[port][tick_idx] = Port.UNUSED
                
                # Now remark all ports based on current operation times
                for child_op, parent_op, route_obj in routes:
                    # The route stores which ports were originally selected
                    src = route_obj.src
                    dst = route_obj.dst
                    
                    # Remark EXIT at parent's current end_time
                    if parent_op.end_time < len(parent_op.module.used_ports[src]):
                        parent_op.module.used_ports[src][parent_op.end_time] = Port.EXIT
                        #print(f"Remarked EXIT port at {src} for {parent_op.id} at time {parent_op.end_time}")
                    
                    # Remark ENTRANCE at child's current start_time  
                    if child_op.start_time < len(child_op.module.used_ports[dst]):
                        child_op.module.used_ports[dst][child_op.start_time] = Port.ENTRANCE
                        #print(f"Remarked ENTRANCE port at {dst} for {child_op.id} at time {child_op.start_time}")

                for op in ops:
                    if op.start_time >= old_start:
                        #print(f"After delay, operation {op.id} starts at {op.start_time} and ends at {op.end_time}")
                        used_exits = [
                            pos
                            for pos, port_type in op.module.used_ports.items()
                            if port_type[op.end_time] == Port.EXIT
                        ]
                        used_entrances = [
                            pos
                            for pos, port_type in op.module.used_ports.items()
                            if port_type[op.start_time] == Port.ENTRANCE
                        ]

                        if op.type is Type.INPUT_0 or op.type is Type.INPUT_1:
                            assert (
                                len(used_exits) == 1
                            ), f"Operation {op.id} of type {op.type} has no exits at start time {op.start_time} after delay!"
                        elif op.type is Type.OUTPUT or op.type is Type.WASTE:
                            assert (
                                len(used_entrances) == 1
                            ), f"Operation {op.id} of type {op.type} has no entrances at end time {op.end_time} after delay!"
                        elif op.type is Type.MIX:
                            # We have 2,
                            # cases one parent is mix, neither parent is mix
                            if len(op.children) == 1:
                                # output case, only 1 exit
                                assert (
                                    len(used_exits) == 1
                                ), f"Operation {op.id} of type MIX has no exits at start time {op.start_time} after delay!"
                            elif any(parent.type is Type.MIX for parent in op.parents) and any(
                                child.type is Type.MIX for child in op.children
                            ):
                                # If both a parent and child are MIX, we may have 3 entrances/exits due to the way we route between MIX modules. In this case, we just check that there are at least 2.
                                assert (
                                    len(used_entrances) == 1
                                ), f"Operation {op.id} of type MIX doesnt have 1 entrance at start time {op.end_time} after delay!"
                                assert (
                                    len(used_exits) == 1
                                ), f"Operation {op.id} of type MIX doesnt have 1 exits at end time {op.start_time} after delay!"
                            elif any(parent.type is Type.MIX for parent in op.parents) and not any(
                                child.type is Type.MIX for child in op.children
                            ):
                                assert (
                                    len(used_entrances) == 1
                                ), f"Operation {op.id} of type MIX has doesnt have 1 entrances at start time {op.start_time} after delay!"
                                assert (
                                    len(used_exits) == 2
                                ), f"Operation {op.id} of type MIX doesnt have 2 exits at end time {op.end_time} after delay!"
                            elif not any(parent.type is Type.MIX for parent in op.parents) and any(
                                child.type is Type.MIX for child in op.children
                            ):
                                assert (
                                    len(used_entrances) == 2
                                ), f"Operation {op.id} of type MIX has doesnt have 2 entrances at start time {op.start_time} after delay!"
                                assert (
                                    len(used_exits) == 1
                                ), f"Operation {op.id} of type MIX doesnt have 1 exits at end time {op.end_time} after delay!"
                            elif not any(parent.type is Type.MIX for parent in op.parents) and not any(
                                child.type is Type.MIX for child in op.children
                            ):
                                assert (
                                    len(used_entrances) == 2
                                ), f"Operation {op.id} of type MIX has doesnt have 2 entrances at start time {op.start_time} after delay!"
                                assert (
                                    len(used_exits) == 2
                                ), f"Operation {op.id} of type MIX doesnt have 2 exits at end time {op.end_time} after delay!"
                        else:
                            assert (
                                len(used_exits) == 1
                            ), f"Operation {op.id} of type {op.type} has no exits at start time {op.start_time} after delay!"
                            assert (
                                len(used_entrances) == 1
                            ), f"Operation {op.id} of type {op.type} has no entrances at end time {op.end_time} after delay!"
                # Add route length frames to protocol
                for _ in range(difference):
                    protocol.insert(parent.end_time + 1, set())
            elif old_start > droplet_arrival:
                for _ in range(0, old_start - droplet_arrival):
                    route.path.insert(0, route.src)
            else:
                pass
        active_ops = [op for op in ops if op.start_time <= i < op.end_time]

        for active_op in active_ops:
            # Convert active operations to protocol frames
            module = active_op.module
            protocol[i].update(module.animation(i, active_op.start_time, active_op.end_time))

        for child, parent, route in active_routes:
            path_idx = i - parent.end_time
            protocol[i].add(route.path[path_idx])

        # Convert positions to board representation
        #board = [["0" for _ in range(16)] for _ in range(8)]
        #for pos in protocol[i]:
        #    board[pos.y][pos.x] = "1"

        # Print board as string representation
        #print(f"Frame {i}:")
        #for row in board:
        #    print("".join(row))

        i += 1
        max_tick = max([op.end_time for op in ops])

    return protocol
