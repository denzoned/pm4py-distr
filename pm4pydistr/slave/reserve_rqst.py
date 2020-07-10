from threading import Thread
import time
from datetime import datetime
from pm4pydistr import configuration
import json
import requests
from pm4pydistr.slave.variable_container import SlaveVariableContainer


class ReserveSlave(Thread):
    def __init__(self, slave, master_host, master_port, unlock):
        # slave is not current one but the one to reserve
        self.slave = slave
        self.conf = None
        self.master_host = master_host
        self.master_port = master_port
        self.unlock = str(unlock)
        Thread.__init__(self)

    def run(self):
        r = requests.get(
            "http://" + self.master_host + ":" + self.master_port + "/reserveSlave?keyphrase=" + configuration.KEYPHRASE + "&slave=" + self.slave + "&unlock=" + self.unlock)
        response = json.loads(r.text)
        self.conf = response['Reservation']
