from threading import Thread
import time
from datetime import datetime
from pm4pydistr import configuration
import requests
from pm4pydistr.slave.variable_container import SlaveVariableContainer


class DoMasterPing(Thread):
    def __init__(self, slave, conf, id, master_host, master_port, pid, host, port):
        self.slave = slave
        self.conf = conf
        self.id = str(id)
        self.host = host
        self.port = port
        self.master_host = master_host
        self.master_port = master_port
        self.pid = pid
        # self.ping = time.time()
        Thread.__init__(self)

    def run(self):
        while True:
            # self.ping = time.time()
            uri = "http://" + self.master_host + ":" + self.master_port + "/pingFromSlave?id=" + str(
                self.id) + "&conf=" + str(self.conf) + "&port" + str(
                self.port) + "&keyphrase=" + configuration.KEYPHRASE
            r = requests.get(uri)
            # print("done ping request")
            # thread sleeps for configuration.SLEEPING_TIME = 30 secs after a request
            time.sleep(configuration.SLEEPING_TIME)
