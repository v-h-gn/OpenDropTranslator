from api.util import Position, path_find
from api.op import Op
from api.module import Module, Port
from api.route import Route

irv = Position.irv


def get_parent_occupied_cells(
    op: Op, occupied_cells: dict[Op, set[Position]]
) -> set[Position]:
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
        for x in range(
            own_mod.pos.x - own_mod.pad, own_mod.pos.x + own_mod.width + own_mod.pad
        ):
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
    ops: list[Op], mods: list[Module], tick: int, routed_ops: set[Op]
) -> list[tuple[Op, Op, Route]]:
    """Get routes for all operations active at the given tick."""

    routes = list[tuple[Op, Op, Route]]()

    # Identify operations active at the current tick
    active_ops = [
        op for op in ops if op.start_time <= tick < op.end_time and op not in routed_ops
    ]
    print(f"Active operations at tick {tick}: {[op.id for op in active_ops]}")
    active_mods = [op.module for op in active_ops]
    occupied_cells: dict[Op, set[Position]] = get_no_go_cells(active_ops, active_mods)

    # Combine all occupied cells into a single set
    occupied = set[Position]()
    for cells in occupied_cells.values():
        occupied.update(cells)

    # Print summary before routing
    print(f"Tick {tick}: Attempting to route {len(active_ops)} active operations.")
    for op in active_ops:
        print(f"Op {op.id} on module {op.module} from {op.start_time} to {op.end_time}")

    # Find routes for each active operation
    for op in active_ops:
        mod = op.module

        # If already routed, skip
        if op in routed_ops:
            print(f"Skipping routing for {op.id} as it has already been routed.")
            continue

        # Route from each parent to this operation
        for parent in op.parents:
            parent_mod = parent.module

            # If parent and child are on the same module, skip routing
            if parent_mod == mod:
                print(
                    f"Skipping routing from {parent.id} to {op.id} as both are on the same module {mod.id}."
                )
                continue

            src, dst = parent_mod.get_nearest_ports(tick, mod)

            parent_mod.used_ports[src][tick] = Port.EXIT
            mod.used_ports[dst][tick] = Port.ENTRANCE
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
                print(
                    f"Successfully routed from {parent.id} of type {parent.type} to {op.id} of type {op.type}"
                )
                routed_ops.add(op)
            except RuntimeError as e:
                print(f"Failed to route from {parent.id} to {op.id}: {e}")
                print(
                    f"Parent module: {parent_mod} at {src}, Child module: {mod} at {dst}"
                )
                raise e

    return routes


def all_cycle_IRV(route: Route, compact_route: Route, cycle: int) -> bool:
    """Check for Interference Region Violation (IRV) at a specific cycle between two routes."""
    r_pos = route.path[cycle]
    cr_pos = compact_route.path[cycle]
    r_pos_prev = route.path[cycle - 1] if cycle - 1 >= 0 else None
    cr_pos_prev = compact_route.path[cycle - 1] if cycle - 1 >= 0 else None
    r_pos_next = route.path[cycle + 1] if cycle + 1 < len(route.path) else None
    cr_pos_next = (
        compact_route.path[cycle + 1] if cycle + 1 < len(compact_route.path) else None
    )

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
                route.stall(cycle)
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


def convert_to_protocol(
    ops: list[Op], routes: list[tuple[Op, Op, Route]]
) -> list[set[Position]]:
    """Convert scheduled operations and routes to a frame-based protocol."""

    max_tick = max(op.end_time for op in ops)

    protocol = [set[Position]() for _ in range(max_tick + 1)]

    for i in range(max_tick + 1):
        # For each tick, determine which operations are active and which routes are active
        active_ops = [op for op in ops if op.start_time <= i < op.end_time]
        print(f"Tick {i}: Active operations: {[op.id for op in active_ops]}")
        active_routes = [
            route
            for route in routes
            if route[1].end_time <= i < route[1].end_time + len(route[2].path)
        ]
        print(f"Tick {i}: Active routes: ["
              + ", ".join(f"{r[1].id}->{r[0].id}" for r in active_routes)
                + "]")

        for active_op in active_ops:
            # Convert active operations to protocol frames
            
            module = active_op.module
            protocol[i].update(
                module.animation(i, active_op.start_time, active_op.end_time)
            )

        for child, parent, route in active_routes:
            droplet_arrival = parent.end_time + len(route.path)

            difference = droplet_arrival - child.start_time
            
            # If the child operation starts before the droplet arrives
            if child.start_time < droplet_arrival:
                # delay child operation to start when droplet arrives
                child.delay(difference)
                # for each port, extend by number of added frames
                for lists in child.module.used_ports.values():
                    for _ in range(difference):
                        lists.insert(parent.end_time + 1, Port.UNUSED)
                # Add route length frames to protocol
                for _ in range(difference):
                    protocol.insert(parent.end_time + 1, set())

        for child, parent, route in active_routes:
            path_idx = i - parent.end_time
            protocol[i].add(route.path[path_idx])
                
        # Convert positions to board representation
        board = [["0" for _ in range(16)] for _ in range(8)]
        for pos in protocol[i]:
            board[pos.y][pos.x] = "1"

        # Print board as string representation
        print(f"Frame {i}:")
        for row in board:
            print("".join(row))

    return protocol
