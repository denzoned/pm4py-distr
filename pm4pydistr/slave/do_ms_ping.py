from threading import Thread
import time
from datetime import datetime
from pm4pydistr import configuration
import json
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
        self.memory = None
        self.CPUpct = None
        self.CPUload = None
        self.diskusage = None
        self.temp = None
        self.os = None
        self.iowait = None
        # self.ping = time.time()
        Thread.__init__(self)

    def run(self):
        while True:
            # self.ping = time.time()
            uri = "http://" + self.master_host + ":" + self.master_port + "/pingFromSlave?id=" + str(
                self.id) + "&conf=" + str(self.conf) + "&port" + str(
                self.port) + "&keyphrase=" + configuration.KEYPHRASE
            r = requests.get(uri)

            uri2 = "http://" + self.master_host + ":" + self.port + "/getResources?keyphrase=" + configuration.KEYPHRASE
            r2 = requests.get(uri2)
            data = json.loads(r2.text)
            #print(data)
            #print(data['cpuload'])
            self.memory = data['memory']
            self.CPUpct = data['cpupct']
            self.CPUload = data['cpuload']
            self.diskusage = data['diskusage']
            self.temp = data['temp']
            self.os = data['os']
            self.iowait = data['iowait']
            print(str(self.memory))

            uri2 = "http://" + self.master_host + ":" + self.master_port + "/sendRes?id=" + str(self.id) + "&conf=" + str(self.conf) + "&port=" + str(self.port) + "&keyphrase=" + configuration.KEYPHRASE + "&memory=" + str(self.memory) + "&CPUpct=" + str(self.CPUpct) + "&CPUload=" + str(self.CPUload) + "&diskusage=" + str(self.diskusage) + "&temp=" + str(self.temp) + "&os=" + str(self.os) + "&iowait=" + str(self.iowait)
            r2 = requests.get(uri2)
            # print("done ping request")
            # thread sleeps for configuration.SLEEPING_TIME = 30 secs after a request
            time.sleep(configuration.SLEEPING_TIME)
