from threading import Thread
import time
from datetime import datetime
from pm4pydistr import configuration
import json
import requests
from pm4pydistr.slave.variable_container import SlaveVariableContainer


class CalcDfg(Thread):
    def __init__(self, slave, conf, target_host, target_port, filename):
        self.slave = slave
        self.conf = conf
        self.target_host = target_host
        self.target_port = target_port
        self.content = None
        self.filename = filename
        Thread.__init__(self)

    def run(self):
        uri = "http://" + self.target_host + ":" + self.target_port + "/sendDFG?keyphrase=" + configuration.KEYPHRASE
        # Might check if it works on bigger files
        with open(self.content) as f:
            data = json.load(f)
        r = requests.post(uri, json=data)
        self.content = json.loads(r.text)
