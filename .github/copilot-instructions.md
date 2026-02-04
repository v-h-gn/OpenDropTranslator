# AI Coding Agent Instructions for OpenDropTranslator

## Project Overview
OpenDropTranslator is a microfluidic protocol compiler that translates operation graphs (defined in DOT format) into executable instruction sequences for OpenDrop digital microfluidic chips. It implements a four-stage pipeline: graph parsing → scheduling → placement → routing.

## Architecture & Data Flow

### Core Pipeline (translator.py)
1. **Parse**: Load DOT graph via `api.op.load_ops_from_dot()` → creates `Op` objects with dependency graph
2. **Schedule**: `scheduler.list_scheduler()` → assigns start/end times using list scheduling (critical path heuristic)
3. **Place**: `placer.left_edge_bind_modules()` → binds scheduled ops to physical `Module` instances
4. **Route**: `router.route()` → finds droplet paths between modules using Lee's algorithm

### Key Data Structures (api/)
- **Op**: Represents an operation (mix, heat, detect, input, output, storage, waste). Has `start_time`, `end_time`, `module` binding, and dependency links (`parents`/`children`). Special subclasses: `InputOp`, `OutputOp`, `StorageOp`, `WasteOp`.
- **Module**: Physical chip location with position, type, ports, capacity (`Holder`). Track `end_time` for availability checks.
- **Position**: (x, y) grid coordinates with `irv()` interference region violation detection (±1 cell proximity).
- **Route**: Stores source, destination, and path (list of Positions).
- **Type enum**: MIX, HEAT, INPUT_0, INPUT_1, OUTPUT, STORAGE, WASTE.

### Critical Conventions
- **Droplet lifetime**: Enters via InputOp → operations chain → exits via OutputOp or WasteOp
- **Time representation**: Integer ticks; operations have exclusive [start_time, end_time) intervals
- **Module availability**: `module.available(tick)` checks if `module.end_time <= tick`
- **Port tracking**: Modules track `used_ports` per operation tick to prevent conflicts
- **Interference zones**: Two droplets violate if within irv (Manhattan dist ≤ 2 in 2D grid)

## Common Developer Workflows

### Running Translation
```bash
python translator.py <input.dot> <output.json> --module_topology <modules.json> --width 16 --height 8
```
- Input: DOT graph + optional module JSON topology
- Output: JSON instruction sequence with electrode states per frame
- Key parameters: board dimensions (width/height), module counts (--heaters, --mixers, etc.)

### Testing
```bash
python test.py
# Runs scheduler/placer tests on smallgraph.dot, mediumgraph.dot, largegraph.dot
```

### Debugging Workflows
1. **Scheduler issues**: Check `can_schedule()` logic in scheduler.py—verify parent dependencies and module availability
2. **Placement conflicts**: Inspect `left_edge_bind_modules()` port tracking; ops on same module must not overlap
3. **Routing failures**: Lee's algorithm in `router.path_find()` uses no_go_cells set; debug via `get_no_go_cells()` output
4. **Output validation**: Check `dispense.json` frame lookup in `get_dispense_frames()` for accurate electrode states

## Project-Specific Patterns

### Operation Dependency Graph
- Ops form a DAG with multiple entry points (InputOps) and exit points (OutputOp/WasteOp)
- Use `op.parents_scheduled()` to verify predecessor completion before scheduling
- Call `op.critical_path_length()` recursively to guide heuristic scheduling

### List Scheduling Strategy
- Sorts candidate operations by critical path (shortest first)
- Respects constraints: parent op completion, available modules, droplet budget (`max_droplets`)
- Each tick, processes terminating ops (freeing modules), then schedules ready ops

### Left-Edge Binding
- Pre-sorts ops by (start_time, end_time) per module type
- Greedily assigns earliest-starting unbound op to first available module
- No op overlap on a module—`module.end_time` is exclusive end time

### Lee's Algorithm Routing
- BFS pathfinding with "no-go cells" encompassing other modules + padding
- Returns first complete route; may require multiple runs if droplets conflict
- Handles board_size bounds; default 16x8 but configurable

## Integration Points & Dependencies
- **NetworkX**: DOT parsing via `networkx.drawing.nx_pydot.read_dot()` (api/op.py)
- **JSON I/O**: Module topology and output instructions (modules.json, output.json)
- **External protocol**: `dispense.json` maps reservoir positions to electrode frame sequences
- **numpy**: May be imported for future matrix operations (see translator.py imports)

## Important Edge Cases
1. **Scheduling deadlock**: If `max_droplets` exhausted before all ops scheduled, increase limit or reduce parallelism
2. **No route found**: `path_find()` raises RuntimeError if target unreachable—check board size, module padding, and interference zones
3. **Module reuse**: Same module instance reused across ops; verify `end_time` updates correctly in placer
4. **Dispense frames**: Only 4 reservoir positions supported; validate input positions in `get_dispense_frames()`
