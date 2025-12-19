import sys
from networkx.drawing.nx_pydot import read_dot

# INFO ABOUT ONE OPERATION
class Operation:
    def __init__(self, name, duration=1, is_input=False):
        self.name = name
        self.duration = duration
        self.is_input = is_input
        self.parents = []
        self.children = []
        self.start_time = None
        self.end_time = None
        self.module_assigned = None

# LOAD OPERATIONS FROM DOT FILE AND RETURN LIST 
def load_ops_from_dot(filepath):
    bigG = read_dot(filepath)
    op_dict = {}
    mix_shit = []
    
    # CREATE ALL THE OPERATIONS
    for nid, attrs in bigG.nodes(data=True):
        label = (attrs.get("label") or "").strip('"')
        if label == "mix":
            op_dict[nid] = Operation(nid, duration=3, is_input=False)
            mix_shit.append(nid)
        elif label.startswith("(") and label.endswith(")"):
            op_dict[nid] = Operation(nid, duration=1, is_input=True)
        else:
            op_dict[nid] = Operation(nid, duration=3, is_input=False)
    
    # CONNECT PARENTS AND CHILDREN  
    for src, dst in bigG.edges():
        op_dict[src].children.append(op_dict[dst])
        op_dict[dst].parents.append(op_dict[src])
    
    # ADD WASTE NODES FOR MIX OPERATIONS
    for nid in mix_shit:
        cudi_count = 0
        for edgy in bigG.edges():
            if edgy[0] == nid:
                cudi_count += 1
        
        if cudi_count == 1:
            useless_dumb_shit = Operation("waste_" + nid, duration=0, is_input=True)
            op_dict[useless_dumb_shit.name] = useless_dumb_shit
            op_dict[nid].children.append(useless_dumb_shit)
            useless_dumb_shit.parents.append(op_dict[nid])
    
    return list(op_dict.values())

# THE MAIN SCHEDULER FUNCTION - ASSIGNS START AND END TIMES
def list_scheduler(ops, available_modules):
    tick = 0
    done_list = []
    running_rn = []  # OPERATIONS CURRENTLY EXECUTING
    modules_busy = 0
    
    print("Time Step", tick)
    
    # KEEP GOING UNTIL ALL OPERATIONS ARE DONE
    max_loops = 1000
    loop_count = 0
    while loop_count < max_loops:
        loop_count += 1
        
        # CHECK IF ANY RUNNING OPERATIONS FINISHED
        just_finished = []
        for op in running_rn:
            if op.end_time == tick:
                just_finished.append(op)
        
        # REMOVE FINISHED OPERATIONS FROM RUNNING LIST
        for op in just_finished:
            running_rn.remove(op)
            if not op.is_input:
                modules_busy -= 1
        
        # FIND OPERATIONS THAT ARE READY TO SCHEDULE
        ready_bois = []
        for op in ops:
            # SKIP IF ALREDY SCHEDULED
            if op.start_time is not None:
                continue
            
            # CHECK IF ALL PARENTS ARE DONE
            parents_done = True
            for parent in op.parents:
                if parent.end_time is None or parent.end_time > tick:
                    parents_done = False
                    break
            
            if parents_done:
                ready_bois.append(op)
        
        # SCHEDULE READY OPERATIONS
        did_something = False
        for op in ready_bois:
            # INPUTS CAN ALWAYS BE SCHEUDLED
            if op.is_input:
                op.start_time = tick
                op.end_time = tick + op.duration
                op.module_assigned = "input-*"
                running_rn.append(op)
                done_list.append(op)
                did_something = True
            # NON INPUTS NEED FREE MODULE
            elif modules_busy < available_modules:
                modules_busy += 1
                op.start_time = tick
                op.end_time = tick + op.duration
                op.module_assigned = "Module " + str(modules_busy)
                running_rn.append(op)
                done_list.append(op)
                did_something = True
        
        # CHECK IF DONE
        all_done = True
        for op in ops:
            if op.start_time is None:
                all_done = False
                break
        
        if all_done:
            break
        
        tick += 1
        print("Time Step", tick)
    
    print("\nFinal Schedule is going to be the following, ")
    
    # SORT BY START TIME AND THEN NAME
    for i in range(len(done_list)):
        for j in range(len(done_list) - 1):
            op1 = done_list[j]
            op2 = done_list[j + 1]
            if op1.start_time > op2.start_time:
                # SWAP 
                tmp = done_list[j]
                done_list[j] = done_list[j + 1]
                done_list[j + 1] = tmp
            elif op1.start_time == op2.start_time:
                if op1.name > op2.name:
                    # SWAP PART 2
                    tmp = done_list[j]
                    done_list[j] = done_list[j + 1]
                    done_list[j + 1] = tmp
    
    for op in done_list:
        print(op.name, "starts at", op.start_time, "ends at", op.end_time, "on", op.module_assigned)

if __name__ == "__main__":
    dot_file = sys.argv[1] if len(sys.argv) > 1 else "mygraph.dot"
    all_ops = load_ops_from_dot(dot_file)
    list_scheduler(all_ops, available_modules=2)