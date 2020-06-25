import requests
import json

from pm4pydistr import configuration


class SlaveRequests:
    def __init__(self, slave, host, port, master_host, master_port, conf):
        self.slave = slave

        self.host = host
        self.port = port
        self.master_host = master_host
        self.master_port = master_port
        self.conf = conf
        self.id = None
        self.pid = None
        self.content = None

    def register_to_webservice(self):
        r = requests.get(
            "http://" + self.master_host + ":" + self.master_port + "/registerSlave?keyphrase=" + configuration.KEYPHRASE + "&ip=" + self.host + "&port=" + self.port + "&conf=" + self.conf)

        response = json.loads(r.text)
        self.id = response['id']
        self.slave.id = response['id']

        r2 = requests.get(
            "http://" + self.host + ":" + self.port + "/getcurrentPIDinfo?keyphrase=" + configuration.KEYPHRASE)

        response = json.loads(r2.text)
        self.slave.pid = response['PID']

        self.slave.enable_ping_of_master()

    def get_pid(self):
        r = requests.get(
            "http://" + self.host + ":" + self.port + "/getcurrentPIDinfo?keyphrase=" + configuration.KEYPHRASE)

        response = json.load(r.text)
        response = response['PID']
        return response

    def get_best_slave(self):
        r = requests.get(
            "http://" + self.master_host + ":" + self.master_port + "/getBestSlave?keyphrase=" + configuration.KEYPHRASE)

        response = json.loads(r.text)
        response = list(response['Slaves'])
        return response
