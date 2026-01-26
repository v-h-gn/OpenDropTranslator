import heapq

from api.op import Op
from api.module import Module
from api.util import Position
from api.route import Route

irv = Position.irv

def print_route(route: Route, board_size: tuple[int, int] = (16, 8), no_go_cells: set[Position] =set() ) -> None:
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
    q = [(0, init_route)]
    heapq.heapify(q)
    visited = {src}
    route = init_route
    while q:
        _, route = heapq.heappop(q)
        if route.dst == dst:
            return route
        for neighbor in route.dst.get_valid_neighbors(board_size):
            if neighbor not in visited and neighbor not in no_go_cells:
                visited.add(neighbor)
                new_route = Route(route.src, neighbor, route.path + [neighbor])
                heapq.heappush(q, (len(new_route.path) + neighbor.manhattan_distance(dst), new_route))
    print_route(route, board_size, no_go_cells)
    raise RuntimeError(f"No route found from {src} to {dst}")

def get_routes(ops: list[Op], mods: dict[str, Module], tick: int) -> list[tuple[str, Route]]:
    """Get routes for all operations active at the given tick."""
    routes = list[tuple[str, Route]]()

    # Identify operations active at the current tick
    active_ops = [op for op in ops if op.start_time <= tick < op.end_time]
    occupied_cells: set[Position] = set()

    # Mark occupied cells based on active operations
    for op in active_ops:
        mod = mods[op.module]
        for x in range(mod.pos.x, mod.pos.x + mod.height):
            for y in range(mod.pos.y, mod.pos.y + mod.width):
                occupied_cells.add(Position(x, y))
    # Find routes for each active operation
    for op in active_ops:
        mod = mods[op.module]
        
        for parent in op.parents:
            parent_mod = mods[parent.module]
            route = path_find(
                src=parent_mod.retrieve(),
                dst=mod.store(),
                no_go_cells=occupied_cells,
                board_size=(16, 8),
            )
            routes.append((f"Route {parent.id}-{op.id}", route))
        

    return routes

def compact_routes(routes: list[tuple[str, Route]]) -> None:
    """Parallelize sequential routes while respecting interference regions, adding stalls if necessary."""
    compacted_routes = list[Route]()
    for _, route in routes:
        route_must_stall = False
        cycle = 0
        while cycle < len(route.path):
            current_pos = route.path[cycle]
            # Check for interference with other routes
            for other_route in compacted_routes:
                if cycle < len(other_route.path):
                    other_pos = other_route.path[cycle]
                    if irv(current_pos, other_pos):
                        route_must_stall = True
                        break
            
            if route_must_stall:
                # Insert a stall by repeating the current position
                route.path.insert(cycle, current_pos)
                route_must_stall = False
            else:
                cycle += 1
        compacted_routes.append(route)

def route(ops: list[Op], mods: dict[str, Module]) -> list[tuple[str, Route]]:
    """Routes droplets between operations based on their module assignments."""

    results = list[tuple[str, Route]]()

    # Ensure ops are sorted by start time
    ops_sorted: list[Op] = sorted(ops, key=lambda o: o.start_time)

    tick = 0
    while ops_sorted:
        sub_routes = get_routes(ops, mods, tick)

        compact_routes(sub_routes)

        results.extend(sub_routes)

        tick += 1
        ops_sorted = [op for op in ops_sorted if op.end_time > tick]
        
    return results
