class MasterVariableContainer:
    port = -1
    master = None
    dbmanager = None
    first_loading_done = False
    log_assignment_done = False
    slave_loading_requested = False
    master_initialization_done = False
    assign_request_threads = []
    assign_dfg_request_threads = []
    init_dfg_calc = False
    best_slave = {}
    ram_multiplier = 1
    cpu_multiplier = 1
    disk_multiplier = 1
    k_slope = 10
    tree_found = False
    found_cut = ""
    send_dfgs = {}
    all_resources_received = False
    reserved_slaves = {}
    created = False
