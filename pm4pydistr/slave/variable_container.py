class SlaveVariableContainer:
    host = None
    port = -1
    master_host = None
    master_port = -1
    conf = None
    pid = None
    memory = None
    cpupct = None
    cpuload = None
    received_dfgs = {}
    send_dfgs = {}
    found_cuts = {}
    managed_logs = {}
    managed_dfgs = {}
    bandwidth = 800000
    network_multiplier = 100
