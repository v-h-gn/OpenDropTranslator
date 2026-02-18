from api.op import Op, Module

from api.util import Type

def left_edge_bind_modules(
    scheduled_ops: list[Op], modules: list[Module], bindable_modules: list[Type]
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
                removes = set[Op]()
                for i in range(len(op_list)):
                    if op_list[i].start_time >= module.end_time:
                        op_list[i].module = module
                        module.end_time = op_list[i].end_time
                        op_list[i].bound = True
                        removes.add(op_list[i])
                for op in removes:
                    op_list.remove(op)
                module.reset_ports()

