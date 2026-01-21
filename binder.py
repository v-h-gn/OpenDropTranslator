from api import Op, Module, Holder

def left_edge_bind_modules(V: list[Op], fixedMods: dict[str, list[Module]], valid_modules: list[str]) -> None:
    # WE MAP EACH ACTIVE OPERATION TO A REAL PHYSICAL MODULE -> NO STORAGE OR IO
    buckets: dict[str, list[Op]] = {}
    for op in V:
        if op.type not in valid_modules:
            module_type = op.module or op.type
            buckets.setdefault(module_type, []).append(op) # PUT OPERATIONS INTO BUCKETS BASED ON MODTYPE
    
    # PUT EARLIEST ONES FIRST
    for module_type in buckets:
        buckets[module_type].sort(key=lambda o: (o.start, o.end))
    
    # GO THROUGH EVERY MODULE TYPE
    for module_type, mods in fixedMods.items():
        op_list = buckets.get(module_type, [])
        for m in mods: 
            i = 0
            while i < len(op_list):
                op = op_list[i]
                # IF OPERATION START GREATER THAN MODULES LAST END THEN IT IS FREE
                if op.start >= m.last_op_end:
                    op.module = m.id
                    m.last_op_end = op.end
                    op_list.pop(i)
                else:
                    i += 1

def bind_storage_to_holders(storage_shit: list[Op], holder_bois: list[Holder]) -> None:
    # SORT THIS SHIT BY TIME STORAGE WAIT TIMES IN ORDER
    storage_shit.sort(key=lambda s: (s.start, s.end))
    # SORT FIRST BY FIXED MODULE LOCATION THEN BY TIME
    holder_bois.sort(key=lambda h: (h.id, h.start, h.end))
    
    i = 0
    while i < len(storage_shit):
        s = storage_shit[i]
        cur_end = 0
        j = 0
        while j < len(holder_bois):
            hb = holder_bois[j]
            # WHEN WE DONT COVER AND HOLDER WINDOW BEGINS AFTER S START AND HAS ROOM
            if (not s.bound) and (s.start == hb.start) and (hb.used + s.size <= hb.cap):
                s.module = hb.id
                hb.used += s.size
                s.bound = True
                cur_end = hb.end
            # AFTER PUTTING THE DROPLET WE EXTEND THE STORAGE INTERVAL
            elif s.bound and (hb.start < cur_end) and (hb.used + s.size <= hb.cap) and (s.module == hb.id):
                hb.used += s.size
                cur_end = hb.end
            # IF NO ROOM IN NEXT HOLDER AND OVERLAP WE SPLIT 
            elif s.bound and (hb.start < cur_end) and (s.module == hb.id) and (hb.used + s.size > hb.cap):
                s2 = Op(s.name + "_tail", "storage", duration=s.end-cur_end, start=cur_end, end=s.end, size=s.size, module=s.module, bound=False)
                s.end = cur_end
                storage_shit.insert(i + 1, s2)
                break
            j += 1
        if cur_end == s.end:
            storage_shit.pop(i)
        else:
            i += 1