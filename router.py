from collections import deque
import copy

from api.op import Op
from api.module import Module
from api.util import Position, Type
from api.route import Route


irv = Position.irv

def print_route(route: Route, board_size: tuple[int, int] = (16, 8), no_go_cells: set[Position] = set(), modules: list[Module] = list()) -> None:
    """Prints a visual representation of the route on the board."""
    
    board = [["." for _ in range(board_size[1])] for _ in range(board_size[0])]

    for cell in no_go_cells:
        if cell.valid(board_size):
            board[cell.x][cell.y] = "#"

    for step in route.path:
        if step.valid(board_size):
            board[step.x][step.y] = "o"
        if step == route.src and step.valid(board_size):
            board[step.x][step.y] = "S"
        if step == route.dst and step.valid(board_size):
            board[step.x][step.y] = "D"

    for mod in modules:
        for x in range(mod.pos.x, mod.pos.x + mod.width):
            for y in range(mod.pos.y, mod.pos.y + mod.height):
                if Position(x, y).valid(board_size):

                    if mod.type == Type.INPUT_0 or mod.type == Type.INPUT_1:
                        board[x][y] = "I"
                    elif mod.type == Type.OUTPUT:
                        board[x][y] = "O"
                    elif mod.type == Type.WASTE:
                        board[x][y] = "W"
                    elif mod.type == Type.MIX:
                        board[x][y] = "M"
                    elif mod.type == Type.STORAGE:
                        board[x][y] = "S"
                    elif mod.type == Type.HEAT:
                        board[x][y] = "H"
                    elif mod.type == Type.DETECT:
                        board[x][y] = "D"

                    if Position(x, y) in mod.entrances:
                        board[x][y] = "Մ"
                    if Position(x, y) in mod.exits:
                        board[x][y] = "Ե"

    # take transpose of board
    board_t = list(zip(*board))

    for row in board_t:
        print(" ".join(row))
    print()


def path_find(
    src: Position,
    dst: Position,
    no_go_cells: set[Position] = set(),
    board_size: tuple[int, int] = (16, 8),
) -> Route:
    """Finds a route from src to dst using A* algorithm."""
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
    print_route(route, board_size, no_go_cells)
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

    Let A be a droplet being routed from module M1 to M2.
    The no-go cells for A include all cells occupied by other modules and the internal area of M1 (excluding entrances/exits).
    """

    no_go_cells_by_op: dict[Op, set[Position]] = {}
    for op in ops:
        mod = mods[op.module]
        no_go_cells = set[Position]()
        # Add all module occupied cells
        for other_mod in mods.values():
            for x in range(other_mod.pos.x - other_mod.pad, other_mod.pos.x + other_mod.width + other_mod.pad):
                for y in range(other_mod.pos.y - other_mod.pad, other_mod.pos.y + other_mod.height + other_mod.pad):
                    no_go_cells.add(Position(x, y))
        # Remove entrances of the current module
        for entrance in mod.entrances:
            no_go_cells.discard(entrance)
        for exit in mod.exits:
            no_go_cells.discard(exit)
        # Remove internal area of the current module
        for x in range(mod.pos.x, mod.pos.x + mod.width):
            for y in range(mod.pos.y, mod.pos.y + mod.height):
                no_go_cells.discard(Position(x, y))
        no_go_cells_by_op[op] = no_go_cells
    return no_go_cells_by_op

def get_routes(ops: list[Op], mods: dict[str, Module], tick: int, routed_ops: set[Op]) -> list[tuple[Op, Op, Route]]:
    """Get routes for all operations active at the given tick."""

    routes = list[tuple[Op, Op, Route]]()

    # Identify operations active at the current tick
    active_ops = [op for op in ops if op.start_time <= tick < op.end_time and op not in routed_ops]
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
        print(f"Parent Modules: {[parent.module for parent in op.parents]}")
        print_route(Route(Position(0,0), Position(0,0), []), no_go_cells=occupied_cells[op], modules=list(active_mods.values()))

    # Find routes for each active operation
    for op in active_ops:
        mod = mods[op.module]
        mod.storage.stored_droplets = 0  # Reset storage for routing purposes
        for parent in op.parents:
            parent_mod = mods[parent.module]

            if parent_mod == mod:
                print(f"Skipping routing from {parent.id} to {op.id} as both are on the same module {mod.id}.")
                continue

            src = parent_mod.retrieve()
            dst = mod.store()
            try:
                route = path_find(
                    src=src,
                    dst=dst,
                    no_go_cells=occupied_cells[op],
                    board_size=(16, 8),
                )
                routes.append((op, parent, route))
                print(f"Successfully routed from {parent.id} of type {parent.type} to {op.id} of type {op.type}")
                print_route(route, no_go_cells=occupied_cells[op], modules=list(active_mods.values()))
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
