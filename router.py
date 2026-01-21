from collections import deque
from api import Op, Module, Position, Route

irv = Position.irv


def soukup(
    src: Position,
    dst: Position,
    no_go_cells: set[Position],
    board_size: tuple[int, int] = (20, 20),
) -> Route:
    init_route = Route(src, src, [src])
    q = deque([init_route])
    visited = {src}
    while q:
        route = q.popleft()
        if route.dst == dst:
            return route
        for neighbor in route.dst.get_valid_neighbors(board_size):
            if neighbor not in visited and neighbor not in no_go_cells:
                visited.add(neighbor)
                q.append(Route(route.src, neighbor, route.path + [neighbor]))
    raise RuntimeError(f"No route found from {src} to {dst}")


# MAIN ROUTER BLW
def route(ops: list[Op], mods: dict[str, Module]) -> list[tuple[str, Route]]:
    """Routes droplets between operations based on their module assignments."""
    pass

    results = list[tuple[str, Route]]()

    # Ensure ops are sorted by start time
    ops_sorted = sorted(ops, key=lambda o: o.start_time)

    for op in ops_sorted:
        module = mods[op.module]
        enter_cell = module.entrance
        exit_cell = module.exit

    return results
