from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Op: # OPERATION IN SCHEDULE
    name: str # M1
    typ: str # MIX HEAT
    start: int
    end: int
    size: int = 1
    ModType: Optional[str] = None
    ModID: Optional[str] = None # WHICH MODULE IT IS ASSIGNRD BINDED TO
    bound: bool = False

@dataclass
class Module: # CHIP MODULE
    ModID: str # MIX-0
    ModType: str # MIX HEAT
    LastOpEnd: int = 0
    slots: List[Op] = field(default_factory=list) # THE OPERATIONS THAT ASSIGNS TO THIS MODULE
    pos: Tuple[int,int,int,int] = (0,0,3,3)
    pad: int = 1 # RED BORDER  

@dataclass
class Holder: # STORAGE CAPACITY FOR MODULE 
    name: str
    ModID: str # WHICH MODULE DOES HOLDER BELONG TO
    start: int
    end: int # WHEN WINDOW IS AVAILABLE
    cap: int = 2 # HOW MANY DROPLETS  
    used: int = 0  

def left_edge_bind_modules(V: List[Op], fixedMods: Dict[str, List[Module]]) -> None:
    # WE MAP EACH ACTIVE OPERATION TO A REAL PHYSICAL MODULE -> NO STORAGE OR IO
    buckets: Dict[str, List[Op]] = {}
    for op in V:
        if op.typ not in ("storage", "input", "output"):
            mt = op.ModType or op.typ
            buckets.setdefault(mt, []).append(op) # PUT OPERATIONS INTO BUCKETS BASED ON MODTYPE
    
    # PUT EARLIEST ONES FIRST
    for mt in buckets:
        buckets[mt].sort(key=lambda o: (o.start, o.end))
    
    # GO THROUGH EVERY MODULE TYPE
    for mt, mods in fixedMods.items():
        op_list = buckets.get(mt, [])
        for m in mods: 
            i = 0
            while i < len(op_list):
                op = op_list[i]
                # IF OPERATION START GREATER THAN MODULES LAST END THEN IT IS FREE
                if op.start >= m.LastOpEnd:
                    op.ModID = m.ModID
                    m.LastOpEnd = op.end
                    m.slots.append(op)
                    op_list.pop(i)
                else:
                    i += 1

def bind_storage_to_holders(storage_shit: List[Op], holder_bois: List[Holder]) -> None:
    # SORT THIS SHIT BY TIME STORAGE WAIT TIMES IN ORDER
    storage_shit.sort(key=lambda s: (s.start, s.end))
    # SORT FIRST BY FIXED MODULE LOCATION THEN BY TIME
    holder_bois.sort(key=lambda h: (h.ModID, h.start, h.end))
    
    i = 0
    while i < len(storage_shit):
        s = storage_shit[i]
        cur_end = 0
        j = 0
        while j < len(holder_bois):
            hb = holder_bois[j]
            # WHEN WE DONT COVER AND HOLDER WINDOW BEGINS AFTER S START AND HAS ROOM
            if (not s.bound) and (s.start == hb.start) and (hb.used + s.size <= hb.cap):
                s.ModID = hb.ModID
                hb.used += s.size
                s.bound = True
                cur_end = hb.end
            # AFTER PUTTING THE DROPLET WE EXTEND THE STORAGE INTERVAL
            elif s.bound and (hb.start < cur_end) and (hb.used + s.size <= hb.cap) and (s.ModID == hb.ModID):
                hb.used += s.size
                cur_end = hb.end
            # IF NO ROOM IN NEXT HOLDER AND OVERLAP WE SPLIT 
            elif s.bound and (hb.start < cur_end) and (s.ModID == hb.ModID) and (hb.used + s.size > hb.cap):
                s2 = Op(s.name + "_tail", "storage", cur_end, s.end, s.size, s.ModType, s.ModID, False)
                s.end = cur_end
                storage_shit.insert(i + 1, s2)
                break
            j += 1
        if cur_end == s.end:
            storage_shit.pop(i)
        else:
            i += 1

def small():
    fixedMods = {
        "mix": [
            Module("mix-0", "mix", pos=(2,2,3,3), pad=1),
            Module("mix-1", "mix", pos=(10,2,3,3), pad=1),
        ],
        "storage": [
            Module("storage-0", "storage", pos=(6,2,3,3), pad=1),
            Module("storage-1", "storage", pos=(11,2,3,3), pad=1),
        ]
    }

    V = [
        # 4 INPUT NODES
        Op("n0", "input", 0, 1),
        Op("n1", "input", 0, 1),
        Op("n3", "input", 2, 3),
        Op("n5", "input", 4, 5),
        
        # 3 MIX OPERATIONS  
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),
        Op("n6", "mix", 5, 7, ModType="mix"),
    ]

    left_edge_bind_modules(V, fixedMods)

    print("\nModule assignments this is the smallest graph I got:")
    for mt, mods in fixedMods.items():
        for m in mods:
            for op in m.slots:
                print(op.name, op.typ, op.start, op.end, "->", m.ModID)

def extension4():
    fixedMods = {
        "mix": [
            Module("mix-0", "mix", pos=(2,2,3,3), pad=1),
            Module("mix-1", "mix", pos=(10,2,3,3), pad=1),
        ],
        "storage": [
            Module("storage-0", "storage", pos=(6,2,3,3), pad=1),
            Module("storage-1", "storage", pos=(11,2,3,3), pad=1),
        ]
    }

    V = [ 
        Op("n0", "input", 0, 1),
        Op("n1", "input", 0, 1),
        Op("n3", "input", 2, 3),
        Op("n5", "input", 4, 5),
        Op("n7", "input", 6, 7),
         
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),
        Op("n6", "mix", 5, 7, ModType="mix"),
        Op("n8", "mix", 7, 9, ModType="mix"),
    ]

    left_edge_bind_modules(V, fixedMods)

    print("\nModule assignments 4 extension:")
    for mt, mods in fixedMods.items():
        for m in mods:
            for op in m.slots:
                print(op.name, op.typ, op.start, op.end, "->", m.ModID)


def extension5():
    fixedMods = {
        "mix": [
            Module("mix-0", "mix", pos=(2,2,3,3), pad=1),
            Module("mix-1", "mix", pos=(10,2,3,3), pad=1),
        ],
        "storage": [
            Module("storage-0", "storage", pos=(6,2,3,3), pad=1),
            Module("storage-1", "storage", pos=(11,2,3,3), pad=1),
        ]
    }

    V = [ 
        Op("n0", "input", 0, 1),
        Op("n1", "input", 0, 1),
        Op("n3", "input", 2, 3),
        Op("n5", "input", 4, 5),
        Op("n7", "input", 6, 7),
        Op("n9", "input", 8, 9),
         
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),
        Op("n6", "mix", 5, 7, ModType="mix"),
        Op("n8", "mix", 7, 9, ModType="mix"),
        Op("n10", "mix", 9, 11, ModType="mix"),
    ]

    left_edge_bind_modules(V, fixedMods)

    print("\nModule assignments 5 extension:")
    for mt, mods in fixedMods.items():
        for m in mods:
            for op in m.slots:
                print(op.name, op.typ, op.start, op.end, "->", m.ModID)


def medium():
    fixedMods = {
        "mix": [
            Module("mix-0", "mix", pos=(2,2,3,3), pad=1),
            Module("mix-1", "mix", pos=(10,2,3,3), pad=1),
        ],
        "storage": [
            Module("storage-0", "storage", pos=(6,2,3,3), pad=1),
            Module("storage-1", "storage", pos=(11,2,3,3), pad=1),
        ]
    }

    V = [
        Op("n0", "input", 0, 1),
        Op("n1", "input", 0, 1),
        Op("n3", "input", 2, 3),
        Op("n5", "input", 4, 5),
        Op("n7", "input", 6, 7),
        Op("n9", "input", 8, 9),
        Op("n11", "input", 10, 11),
        
        Op("n2", "mix", 1, 3, ModType="mix"),
        Op("n4", "mix", 3, 5, ModType="mix"),
        Op("n6", "mix", 5, 7, ModType="mix"),
        Op("n8", "mix", 7, 9, ModType="mix"),
        Op("n10", "mix", 9, 11, ModType="mix"),
        Op("n12", "mix", 11, 13, ModType="mix"),
        
        Op("S1", "storage", 5, 9, size=1, ModType="storage"),
    ]
 
    holder_bois = [
        Holder("h0", "storage-0", 5, 9, cap=1),
    ]

    left_edge_bind_modules(V, fixedMods)
    bind_storage_to_holders([op for op in V if op.typ == "storage"], holder_bois)

    print("\nModule assignments this is the medium graph:")
    for mt, mods in fixedMods.items():
        for m in mods:
            for op in m.slots:
                print(op.name, op.typ, op.start, op.end, "->", m.ModID)

    print("\nStorage bindings:")
    for op in V:
        if op.typ == "storage":
            print(op.name, op.start, op.end, "->", op.ModID)


def big():
    fixedMods = {
        "mix": [
            Module("mix-0", "mix", pos=(2,2,3,3), pad=1),
            Module("mix-1", "mix", pos=(10,2,3,3), pad=1),
        ],
        "storage": [
            Module("storage-0", "storage", pos=(6,2,3,3), pad=1),
            Module("storage-1", "storage", pos=(11,2,3,3), pad=1),
        ]
    }

    V = [
        Op("n2",  "input", 0, 1),
        Op("n5",  "input", 0, 1),
        Op("n7",  "input", 0, 1),
        Op("n9",  "input", 0, 1),
        Op("n11", "input", 0, 1),
        Op("n13", "input", 0, 1),
        Op("n14", "input", 0, 1),
        Op("n17", "input", 0, 1),
        Op("n18", "input", 0, 1),

        Op("n12", "mix", 1, 4, ModType="mix"),
        Op("n16", "mix", 1, 4, ModType="mix"),
        Op("n10", "mix", 4, 7, ModType="mix"),
        Op("n8",  "mix", 7,10, ModType="mix"),
        Op("n15", "mix",10,13, ModType="mix"),
        Op("n6",  "mix",10,13, ModType="mix"),
        Op("n4",  "mix",13,16, ModType="mix"),
        Op("n3",  "mix",16,19, ModType="mix"),
        Op("n1",  "mix",19,22, ModType="mix"),
        Op("n0",  "mix",22,25, ModType="mix"),
        
        Op("S1", "storage", 4, 10, size=1, ModType="storage"),  
        Op("S2", "storage", 4, 13, size=1, ModType="storage"),
    ]

    holder_bois = [
        Holder("h0", "storage-0", 4, 10, cap=1),
        Holder("h1", "storage-1", 4, 13, cap=1),
    ]

    left_edge_bind_modules(V, fixedMods)
    bind_storage_to_holders([op for op in V if op.typ == "storage"], holder_bois)

    print("\nModule assignments this is the biggest graph I got:")
    for mt, mods in fixedMods.items():
        for m in mods:
            for op in m.slots:
                print(op.name, op.typ, op.start, op.end, "->", m.ModID)

    print("\nStorage bindings:")
    for op in V:
        if op.typ == "storage":
            print(op.name, op.start, op.end, "->", op.ModID)

if __name__ == "__main__":
    small()
    print("----------------------------")
    extension4()
    print("----------------------------")
    extension5()
    print("----------------------------")
    medium()
    print("----------------------------")
    big()
    print("----------------------------")