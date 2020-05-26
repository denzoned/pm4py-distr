class MasterVariableContainer:
    port = -1
    master = None
    dbmanager = None
    first_loading_done = False
    log_assignment_done = False
    slave_loading_requested = False
    assign_request_threads = []
    init_dfg_calc = False
    best_slave = 0
    ram_multiplier = 1
    cpu_multiplier = 1
    disk_multiplier = 1
    k_slope = 10

