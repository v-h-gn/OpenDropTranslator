from collections import deque
from binder import Op, Module, left_edge_bind_modules

# WHOLE BOARD
NASHWAANALIKHAN = (14, 6)

# INPUT RESERVOIRS 2 CONCENTRATIONS
# NEED TO MAKE RECONFIGURABLE
INPUT_RESERVOIRS = [
    (0, 0, 0),    # 0  
    (0, 2, 100),  # 100 
]

# WASTE LOCATION ON RIGHT SIDE OF CHIP
DUMB_SHIT = (13, 2)

# GET MODULE ENTRANCE  
def entrance(m):
    x, y, w, h = m.pos
    return (x, y)

# GET MODULE EXIT  
def exit_cell(m):
    x, y, w, h = m.pos
    return (x + w - 1, y)

# FIND WHICH MODULE BOUND TO
def find_mod(op, mods):
    for mod_list in mods.values():
        for m in mod_list:
            if m.ModID == op.ModID:
                return m
    return None

def soukup(src, dst, no_go_zones):
    if src == dst:
        return [src]
    q = deque([(src, [src])])
    been_there = {src}
    while q:
        (x, y), path = q.popleft()
        if (x, y) == dst:
            return path
        # TRY ALL 4 DIRECTIONS
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < NASHWAANALIKHAN[0] and 0 <= ny < NASHWAANALIKHAN[1]:
                if (nx, ny) not in been_there and (nx, ny) not in no_go_zones:
                    been_there.add((nx, ny))
                    q.append(((nx, ny), path + [(nx, ny)]))
    return [src, dst]   

# IRV CHECK  
def irv(p1, p2):
    if p1 is None or p2 is None:
        return False
    return abs(p1[0] - p2[0]) <= 1 and abs(p1[1] - p2[1]) <= 1

# AVOID COLLIDING
def compact_routes(route_list):
    route_list.sort(key=lambda r: len(r), reverse=True)  # LONGEST 
    done_routes = []

    for r in route_list:
        if not done_routes:
            done_routes.append(r)
            continue

        i = 0
        while i < len(r):
            gotta_wait = False
            for cr in done_routes:
                # NEED TO SEE IRV SHIT
                r_i = r[i] if i < len(r) else None
                r_prev = r[i-1] if i > 0 else None
                cr_i = cr[i] if i < len(cr) else None
                cr_prev = cr[i-1] if i > 0 and i-1 < len(cr) else None
                cr_next = cr[i+1] if i+1 < len(cr) else None

                if irv(r_i, cr_prev) or irv(r_i, cr_next) or irv(r_i, cr_i) or irv(r_prev, cr_prev):
                    gotta_wait = True
                    break

            if gotta_wait:
                # ADD STALL HERE
                pos = max(0, i - 2)
                r.insert(pos, r[pos])
            else:
                i += 1

            if len(r) > 100:   
                break

        done_routes.append(r)

    return done_routes

# MAIN ROUTER BLW
def route(V, mods):
    results = []
    mixy_ops = sorted([op for op in V if op.typ == "mix"], key=lambda op: op.start)  # SORT START T
    input_count = 1   

    for i, op in enumerate(mixy_ops):
        mod = find_mod(op, mods)
        ent = entrance(mod)
        ext = exit_cell(mod)

        if i == 0:
            # 2 INPUTS DIFFERENT CONC
            for juice in INPUT_RESERVOIRS:
                src = (juice[0], juice[1])
                conc = juice[2]
                path = soukup(src, ent, set())
                results.append(("Input " + str(input_count) + " (" + str(conc) + "% concentration) to " + op.name, src, ent, path))
                input_count += 1
        else:
            # CHECK GRAPH
            prev_op = mixy_ops[i-1]
            prev_mod = find_mod(prev_op, mods)
            prev_ext = exit_cell(prev_mod)

            # PREVIOUS MIX IN SAME MODULE NO MOVING
            if prev_mod.ModID == mod.ModID:
                results.append((prev_op.name + " to " + op.name, prev_ext, ent, ["STAYS IN MODULE"]))
            else:
                # MOVING TO MODULE ENTRANCE
                path = soukup(prev_ext, ent, set())
                results.append((prev_op.name + " to " + op.name, prev_ext, ent, path))

            # FROM NO CONC RESERVOIR
            src = (INPUT_RESERVOIRS[0][0], INPUT_RESERVOIRS[0][1])
            conc = INPUT_RESERVOIRS[0][2]
            path = soukup(src, ent, set())
            results.append(("Input " + str(input_count) + " (" + str(conc) + "% concentration) to " + op.name, src, ent, path))
            input_count += 1

        # WASTE OUTPUTS
        path = soukup(ent, DUMB_SHIT, set())
        results.append((op.name + " waste route", ent, DUMB_SHIT, path))

    return results

def test_small():
    print("This is the smallest graph I got \n")
    print("")

    fixedMods = {"mix": [Module("mix-0", "mix", pos=(2,2,3,3))]}
    V = [
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),
        Op("n6", "mix", 5, 7, ModType="mix"),
    ]

    left_edge_bind_modules(V, fixedMods)

    print("Bindings:")
    for op in sorted([op for op in V if op.typ == "mix"], key=lambda op: op.start):
        print("  " + op.name + " (" + str(op.start) + "-" + str(op.end) + ") to " + op.ModID)

    print("")
    print("Routes:")
    for name, src, dst, path in route(V, fixedMods):
        if path == ["STAYS IN MODULE"]:
            print("  " + name + ": droplet stays in module (no routing needed)")
        else:
            print("  " + name + ": " + str(src) + " to " + str(dst) + ", this results in " + str(len(path)) + " cycles")

def test_medium():
    print("This is the medium graph I got \n")
    print("")

    fixedMods = {"mix": [Module("mix-0", "mix", pos=(2,2,3,3))]}
    V = [
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),
        Op("n6", "mix", 5, 7, ModType="mix"),
        Op("n8", "mix", 7, 9, ModType="mix"),
        Op("n10", "mix", 9, 11, ModType="mix"),
        Op("n12", "mix", 11, 13, ModType="mix"),
        Op("n14", "mix", 13, 15, ModType="mix"),
    ]

    left_edge_bind_modules(V, fixedMods)

    print("Bindings:")
    for op in sorted([op for op in V if op.typ == "mix"], key=lambda op: op.start):
        print("  " + op.name + " (" + str(op.start) + "-" + str(op.end) + ") to " + op.ModID)

    print("")
    print("Routes:")
    for name, src, dst, path in route(V, fixedMods):
        if path == ["STAYS IN MODULE"]:
            print("  " + name + ": droplet stays in module (no routing needed)")
        else:
            print("  " + name + ": " + str(src) + " to " + str(dst) + ", this results in " + str(len(path)) + " cycles")

def test_largest():
    print("This is the largest graph I got \n")
    print("")

    fixedMods = {"mix": [Module("mix-0", "mix", pos=(2,2,3,3)), Module("mix-1", "mix", pos=(8,2,3,3))]}
    V = [
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),   
        Op("n5", "mix", 3, 5, ModType="mix"),   
        Op("n6", "mix", 5, 7, ModType="mix"),   
        Op("n7", "mix", 5, 7, ModType="mix"),   
        Op("n8", "mix", 7, 9, ModType="mix"),
        Op("n9", "mix", 9, 11, ModType="mix"),
        Op("n10", "mix", 11, 13, ModType="mix"),
        Op("n11", "mix", 13, 15, ModType="mix"),
        Op("n12", "mix", 15, 17, ModType="mix"),
    ]

    left_edge_bind_modules(V, fixedMods)

    print("Bindings:")
    for op in sorted([op for op in V if op.typ == "mix"], key=lambda op: op.start):
        print("  " + op.name + " (" + str(op.start) + "-" + str(op.end) + ") to " + op.ModID)

    print("")
    print("Routes:")
    for name, src, dst, path in route(V, fixedMods):
        if path == ["STAYS IN MODULE"]:
            print("  " + name + ": droplet stays in module (no routing needed)")
        else:
            print("  " + name + ": " + str(src) + " to " + str(dst) + ", this results in " + str(len(path)) + " cycles")

if __name__ == "__main__":
    test_small()
    print("")
    print("=" * 50)
    print("")
    test_medium()
    print("")
    print("=" * 50)
    print("")
    test_largest()