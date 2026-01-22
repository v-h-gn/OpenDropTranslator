from api import Op, Module, Holder

def left_edge_bind_modules(
    scheduled_ops: list[Op], modules: list[Module], bindable_modules: list[str]
) -> None:
    """Bind scheduled operations to physical modules using a left-edge algorithm."""
    
    # Key operations and modules by the type of action they perform.
    ops_by_type = Op.ops_by_type(scheduled_ops)
    modules_by_type = Module.mods_by_type(modules)
    
    # Sort operations of each type by start time (and end time for ties)
    for module_type in ops_by_type:
        ops_by_type[module_type].sort(key=lambda o: (o.start_time, o.end_time))

    # For each module type, bind operations to modules using left-edge strategy
    for module_type, mods in modules_by_type.items():
        # Get the list of operations of this type
        if (module_type in bindable_modules):
            op_list = ops_by_type.get(module_type, [])
            # For each module of this type, while there are unbound operations, bind them
            for module in mods:
                while op_list:
                    op = op_list[0]
                    if op.start_time >= module.end_time:
                        op.module = module.id
                        module.end_time = op.end_time
                        op.bound = True
                        op_list.pop(0)
    
# @TODO HANDLE STORAGE MODULES WITH HOLDERS

def bind_storage_to_holders(storage_shit: list[Op], holder_bois: list[Holder]) -> None:
    # SORT THIS SHIT BY TIME STORAGE WAIT TIMES IN ORDER
    storage_shit.sort(key=lambda s: (s.start_time, s.end_time))
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
            if (
                (not s.bound)
                and (s.start_time == hb.start)
                and (hb.used + s.size <= hb.cap)
            ):
                s.module = hb.id
                hb.used += s.size
                s.bound = True
                cur_end = hb.end
            # AFTER PUTTING THE DROPLET WE EXTEND THE STORAGE INTERVAL
            elif (
                s.bound
                and (hb.start < cur_end)
                and (hb.used + s.size <= hb.cap)
                and (s.module == hb.id)
            ):
                hb.used += s.size
                cur_end = hb.end
            # IF NO ROOM IN NEXT HOLDER AND OVERLAP WE SPLIT
            elif (
                s.bound
                and (hb.start < cur_end)
                and (s.module == hb.id)
                and (hb.used + s.size > hb.cap)
            ):
                s2 = Op(
                    s.name + "_tail",
                    "storage",
                    duration=s.end_time - cur_end,
                    start_time=cur_end,
                    end_time=s.end_time,
                    size=s.size,
                    module=s.module,
                    bound=False,
                )
                s.end_time = cur_end
                storage_shit.insert(i + 1, s2)
                break
            j += 1
        if cur_end == s.end_time:
            storage_shit.pop(i)
        else:
            i += 1
