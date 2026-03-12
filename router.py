from api.util import Position, get_frames, path_find, pos_to_reservoir
from api.op import Op
from api.module import Module, Port, ReservoirModule
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


def get_routes(
    ops: list[Op], mods: list[Module], tick: int, routed_ops: set[Op], all_routes: list[tuple[Op, Op, Route]]
) -> list[tuple[Op, Op, Route]]:
    """Get routes for all operations active at the given tick."""

    routes = list[tuple[Op, Op, Route]]()

    # Identify operations active at the current tick
    active_ops = [op for op in ops if op.start_time <= tick < op.end_time and op not in routed_ops]
    # print(f"Active operations at tick {tick}: {[op.id for op in active_ops]}")
    active_mods = [op.module for op in active_ops]

    occupied_cells: dict[Op, set[Position]] = get_no_go_cells(active_ops, active_mods)

    # Print summary before routing
    print(f"Tick {tick}: Attempting to route {len(active_ops)} active operations.")
    for op in active_ops:
        print(f"Op {op.id} on module {op.module} from {op.start_time} to {op.end_time}")

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
                # print(f"Skipping routing from {parent.id} to {op.id} as both are on the same module {mod.id}.")
                continue

            # check if bi-directional route already exists for this parent-child pair
            existing_route = next((r for r in all_routes if (r[0] == op and r[1] == parent) or (r[0] == parent and r[1] == op)), None)
            if existing_route is not None:
                print(f"Skipping routing from {parent.id} to {op.id} as a route already exists between these operations.")
                continue
            src, dst = Module.get_nearest_ports(parent_mod, mod, parent.end_time, op.start_time)
            # Remove src and dst from occupied cells to allow routing to/from these points
            parent_mod.used_ports[src][parent.end_time] = Port.EXIT

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
                route.start = parent.end_time
                route.end = route.start + len(route.path)
                delay = route.end - op.start_time

                if delay > 0:
                    # print(f"Routing from {parent.id} to {op.id} requires a delay of {delay} ticks. Delaying child operation and all subsequent operations accordingly.")
                    for other_op in ops:
                        if other_op.start_time >= op.start_time:
                            # print(f"Delaying operation {other_op.id} from {other_op.start_time}-{other_op.end_time} to {other_op.start_time + delay}-{other_op.end_time + delay}")
                            other_op.delay(delay, propagate=False)
                elif delay < 0:
                    print(
                        f"Routing from {parent.id} to {op.id} is faster than the scheduled start time by {-delay} ticks. Inserting stalls in the route to delay it accordingly."
                    )
                    for _ in range(0, -delay):
                        route.stall(0)
                route.end = route.start + len(route.path)
                routes.append((op, parent, route))
                mod.used_ports[dst][route.end] = Port.ENTRANCE

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
        or irv(r_pos_next, cr_pos_next)
    )


def compact_routes(routes: list[tuple[Op, Op, Route]], ops: list[Op], tick: int) -> None:
    """Parallelize sequential routes while respecting interference regions, adding stalls if necessary."""
    compacted_routes = list[Route]()
    attempted_ports = set[Position]()
    active_ops = [op for op in ops if op.start_time <= tick < op.end_time]
    active_mods = [op.module for op in active_ops]
    for i, (child, parent, route) in enumerate(routes):
        route_must_stall = False
        MAX_STALLS = 128  # Prevent infinite loops, in worst case we may need to stall at every step
        stalls = 0
        cycle = 0
        # print(f"Compacting route from {route.src} to {route.dst} with initial length {len(route.path)}")
        # print_route(route)
        attempted_ports.add(route.src)
        attempted_ports.add(route.dst)
        while cycle < len(route.path):
            # Check for interference with other routes
            other_route = None
            for other_route in compacted_routes:
                # print(f"Checking interference with route from {other_route.src} to {other_route.dst}")
                # print_route(other_route)
                if route.end <= other_route.start or route.start >= other_route.end:
                    # No temporal overlap, so no interference
                    continue

                if cycle < len(other_route.path) and all_cycle_IRV(route, other_route, cycle):
                    route_must_stall = True
                    break

            if route_must_stall:
                # Insert a stall by repeating the current position
                route.stall(cycle - 2)
                route_must_stall = False
                stalls += 1
                if stalls >= MAX_STALLS and other_route is not None:
                    
                    parent_ports = parent.module.get_unused_ports(parent.end_time)
                    child_ports = child.module.get_unused_ports(child.start_time)

                    src, dst = min([(p1, p2) for p1 in parent_ports for p2 in child_ports if p1 not in attempted_ports and p2 not in attempted_ports], key=lambda pair: pair[0].manhattan_distance(pair[1]))
                    
                    attempted_ports.add(src)
                    attempted_ports.add(dst)

                    parent.module.used_ports[route.src][parent.end_time] = Port.UNUSED
                    child.module.used_ports[route.dst][child.start_time] = Port.UNUSED
                    active_ops.append(child)
                    active_mods.append(child.module)
                    if not parent_ports and not child_ports:
                        print(f"No available ports for rerouting from {parent.id} to {child.id}. Cannot resolve IRV.")
                        raise RuntimeError(f"No available ports for rerouting from {parent.id} to {child.id}. Cannot resolve IRV. Maximum stalls reached: {stalls} for route from {route.src} to {route.dst} vs route from {other_route.src} to {other_route.dst}")
                    try:
                        reroute = Route(
                            src,
                            dst,
                            path_find(
                                src=src,
                                dst=dst,
                                no_go_cells=get_no_go_cells(active_ops, active_mods)[child],
                                board_size=(16, 8),
                            ),
                        )
                        reroute.start = parent.end_time
                        reroute.end = reroute.start + len(reroute.path)
                        route = reroute
                        routes[i] = (child, parent, route)
                        cycle = 0  # Restart compaction for the new route
                        stalls = 0
                        delay = route.end - child.start_time
                        if delay > 0:
                            for other_op in ops:
                                if other_op.start_time >= child.start_time:
                                    other_op.delay(delay, propagate=False)
                        elif delay < 0:
                            for _ in range(0, -delay):
                                route.stall(0)
                        
                        parent.module.used_ports[src][parent.end_time] = Port.EXIT
                        child.module.used_ports[dst][child.start_time] = Port.ENTRANCE
                        active_ops.remove(child)
                    except RuntimeError as e:
                        print(f"Failed to reroute from {parent.id} to {child.id}: {e}")
                        raise e
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
        ops_and_routes = get_routes(ops_sorted, mods, tick, routed_ops=routed_ops, all_routes=results)

        try:
            compact_routes(ops_and_routes, ops, tick)
        except RuntimeError as e:
            print(f"Error during route compaction at tick {tick}: {e}")
            print("Current routes:")
            for r in results:
                print(f"Route from {r[1].id} to {r[0].id} starting at {r[2].start} with path length {len(r[2].path)}")
            raise e

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
        active_routes = [route for route in routes if route[1].end_time <= i < route[1].end_time + len(route[2].path)]

        # print(f"Tick {i}")
        # print(f"Active operations: {[op.id for op in active_ops]}")
        # print(f"Active routes: [" + ", ".join(f"{r[1].id}->{r[0].id}" for r in active_routes) + "]")
        # print("----")

        active_ops = [op for op in ops if op.start_time <= i < op.end_time]

        for child, parent, route in active_routes:
            droplet_arrival = parent.end_time + len(route.path)
            delta_t = child.start_time - droplet_arrival
            if delta_t > 0:
                for _ in range(0, delta_t):
                    route.stall(0)
                child.module.used_ports[route.dst][child.start_time] = Port.ENTRANCE

        for active_op in active_ops:
            # Convert active operations to protocol frames
            module = active_op.module
            protocol[i].update(module.animation(i, active_op.start_time, active_op.end_time))

        for _, parent, route in active_routes:
            # Convert active routes to protocol frames
            path_idx = i - parent.end_time
            protocol[i].add(route.path[path_idx])

        for mod in mods:
            active_mod_ops = [op for op in active_ops if op.module == mod]
            if isinstance(mod, ReservoirModule) and not active_mod_ops:
                reservoir = pos_to_reservoir(mod.pos)
                active_animation = get_frames(f"animations/{reservoir}_active.json")
                protocol[i].update(active_animation[0])

        # Convert positions to board representation
        # board = [["0" for _ in range(16)] for _ in range(8)]
        # for pos in protocol[i]:
        #    board[pos.y][pos.x] = "1"

        # Print board as string representation
        # print(f"Frame {i}:")
        # for row in board:
        #    print("".join(row))

        i += 1
        max_tick = max([op.end_time for op in ops])

    return protocol
