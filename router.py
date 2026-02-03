from collections import deque

from api.op import Op
from api.module import Module
from api.util import Position
from api.route import Route

import copy

irv = Position.irv


def path_find(
    src: Position,
    dst: Position,
    no_go_cells: set[Position] = set(),
    board_size: tuple[int, int] = (16, 8),
) -> Route:
    """Finds a route from src to dst using Lee's algorithm."""
    init_route = Route(src, src, [src])
    q = deque([init_route])
    visited = {src}
    route = init_route
    while q:
        route = q.popleft()
        if route.dst == dst:
            return route
        for neighbor in route.dst.get_valid_neighbors(board_size):
            if neighbor not in visited and neighbor not in no_go_cells:
                visited.add(neighbor)
                new_route = Route(route.src, neighbor, copy.deepcopy(route.path) + [neighbor])
                q.append(new_route)
    raise RuntimeError(f"No route found from {src} to {dst}")

def get_parent_occupied_cells(op: Op, occupied_cells: dict[Op, set[Position]], mods: dict[str, Module]) -> set[Position]:
    """Get occupied cells for all parent operations of the given operation."""
    occupied = set[Position]()
    for parent in op.parents:
        parent_mod = mods[parent.module]
        for x in range(parent_mod.pos.x - parent_mod.pad, parent_mod.pos.x + parent_mod.width + parent_mod.pad):
            for y in range(parent_mod.pos.y - parent_mod.pad, parent_mod.pos.y + parent_mod.height + parent_mod.pad):
                if parent in occupied_cells:
                    occupied.update(occupied_cells[parent])
                else:
                    occupied.add(Position(x, y))
    return occupied

def get_no_go_cells(ops: list[Op], mods: dict[str, Module]) -> dict[Op, set[Position]]:
    """
    Get all no-go cells on the board at a given tick for the provided operations and modules.
    """
    no_go_cells_by_op: dict[Op, set[Position]] = {}
    for op in ops:
        no_go_cells = set[Position]()
        # Add all module occupied cells
        for other_mod in mods.values():
            for x in range(other_mod.pos.x - other_mod.pad, other_mod.pos.x + other_mod.width + other_mod.pad):
                for y in range(other_mod.pos.y - other_mod.pad, other_mod.pos.y + other_mod.height + other_mod.pad):
                    no_go_cells.add(Position(x, y))
        own_mod = mods[op.module]
        for x in range(own_mod.pos.x - own_mod.pad, own_mod.pos.x + own_mod.width + own_mod.pad):
            for y in range(own_mod.pos.y - own_mod.pad, own_mod.pos.y + own_mod.height + own_mod.pad):
                pos = Position(x, y)
                if not own_mod.is_internal(pos):
                    no_go_cells.remove(pos)

        no_go_cells_by_op[op] = no_go_cells
        
    return no_go_cells_by_op

def get_routes(ops: list[Op], mods: dict[str, Module], tick: int, routed_ops: set[Op]) -> list[tuple[Op, Op, Route]]:
    """Get routes for all operations active at the given tick."""

    routes = list[tuple[Op, Op, Route]]()

    # Identify operations active at the current tick
    active_ops = [op for op in ops if op.start_time <= tick < op.end_time and op not in routed_ops]
    print(f"Active operations at tick {tick}: {[op.id for op in active_ops]}")
    active_mods = {op.module: mods[op.module] for op in active_ops}
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
        mod = mods[op.module]
        
        # If already routed, skip
        if op in routed_ops:
            print(f"Skipping routing for {op.id} as it has already been routed.")
            continue

        # Route from each parent to this operation
        for parent in op.parents:
            parent_mod = mods[parent.module]

            # If parent and child are on the same module, skip routing
            if parent_mod == mod:
                print(f"Skipping routing from {parent.id} to {op.id} as both are on the same module {mod.id}.")
                continue

            src, dst = parent_mod.get_nearest_ports(tick, mod)

            parent_mod.used_ports[src][tick] = True
            mod.used_ports[dst][tick] = True
            # Remove src and dst from occupied cells to allow routing to/from these points
            try:
                route = path_find(
                    src=src,
                    dst=dst,
                    no_go_cells=occupied_cells[op] - {src} - {dst},
                    board_size=(16, 8),
                )
                routes.append((op, parent, route))
                print(f"Successfully routed from {parent.id} of type {parent.type} to {op.id} of type {op.type}")
                routed_ops.add(op)
            except RuntimeError as e:
                print(f"Failed to route from {parent.id} to {op.id}: {e}")
                print(f"Parent module: {parent_mod} at {src}, Child module: {mod} at {dst}")
                raise e

    return routes

def all_cycle_IRV(route: Route, compact_route: Route, cycle: int) -> bool:
    """Check for Interference Region Violation (IRV) at a specific cycle between two routes."""
    r_pos = route.path[cycle]
    cr_pos= compact_route.path[cycle] 
    r_pos_prev = route.path[cycle - 1] if cycle - 1 >= 0 else None
    cr_pos_prev = compact_route.path[cycle - 1] if cycle - 1 >= 0 else None
    r_pos_next = route.path[cycle + 1] if cycle + 1 < len(route.path) else None
    cr_pos_next = compact_route.path[cycle + 1] if cycle + 1 < len(compact_route.path) else None

    return irv(r_pos, cr_pos_prev) or irv(r_pos, cr_pos_next) or irv(r_pos_prev, cr_pos) or irv(r_pos_next, cr_pos) or irv(r_pos, cr_pos) or irv(r_pos_prev, cr_pos_prev)

def compact_routes(routes: list[tuple[Op, Op, Route]]) -> None:
    """Parallelize sequential routes while respecting interference regions, adding stalls if necessary."""
    compacted_routes = list[Route]()
    for _, _, route in routes:
        route_must_stall = False
        cycle = 0
        #print(f"Compacting route from {route.src} to {route.dst} with initial length {len(route.path)}")
        #print_route(route)
        while cycle < len(route.path):
            # Check for interference with other routes
            for other_route in compacted_routes:
                #print(f"Checking interference with route from {other_route.src} to {other_route.dst}")
                #print_route(other_route)
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

def route(ops: list[Op], mods: dict[str, Module]) -> list[tuple[Op, Op, Route]]:
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
