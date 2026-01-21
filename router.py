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


def route(ops: list[Op], mods: dict[str, Module]) -> list[tuple[str, Route]]:
    """Routes droplets between operations based on their module assignments."""

    results = list[tuple[str, Route]]()

    # Ensure ops are sorted by start time
    ops_sorted = sorted(ops, key=lambda o: o.start_time)

    for op in ops_sorted:
        module = mods[op.module]
        enter_cell = module.entrance

        for parent in op.parents:
            parent_module = mods[parent.module]
            exit_cell = parent_module.exit

            # Collect no-go cells: occupied modules at this time
            no_go_cells = set[Position]()
            for other_op in ops_sorted:
                if other_op == op or other_op == parent:
                    continue
                if (
                    other_op.start_time <= op.start_time < other_op.end_time
                    or other_op.start_time < parent.end_time <= other_op.end_time
                ):
                    other_module = mods[other_op.module]
                    for dx in range(-other_module.pad, other_module.width + other_module.pad):
                        for dy in range(-other_module.pad, other_module.height + other_module.pad):
                            no_go_cells.add(
                                Position(
                                    other_module.pos.x + dx,
                                    other_module.pos.y + dy,
                                )
                            )

            # Find route from parent exit to current op entrance
            droplet_route = soukup(
                exit_cell,
                enter_cell,
                no_go_cells,
            )
            results.append((f"{parent.name}_to_{op.name}", droplet_route))

    return results
