from threading import Thread
import time
from datetime import datetime
from pm4pydistr import configuration
import json
import requests
from pm4pydistr.slave.variable_container import SlaveVariableContainer


class PostResultTree(Thread):
    def __init__(self, slave, conf, target_host, target_port, tree):
        self.slave = slave
        self.conf = conf
        self.target_host = target_host
        self.target_port = target_port
        self.tree = tree
        Thread.__init__(self)

    def run(self):
        uri = "http://" + self.target_host + ":" + self.target_port + "/sendTree?keyphrase=" + configuration.KEYPHRASE

        r = requests.post(uri, json=self.tree)
