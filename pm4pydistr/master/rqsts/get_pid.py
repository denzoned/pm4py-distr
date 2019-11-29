from pm4pydistr.master.rqsts.basic_request import BasicMasterRequest
from pm4pydistr.configuration import KEYPHRASE
import requests
import json


class PIDRequest(BasicMasterRequest):
    def __init__(self, session, target_host, target_port, use_transition, no_samples, content):
        self.session = session
        self.target_host = target_host
        self.target_port = target_port
        self.content = content
        self.use_transition = use_transition
        self.no_samples = no_samples
        self.pid = None
        BasicMasterRequest.__init__(self, session, target_host, target_port, use_transition, no_samples, content)

    def run(self):
        uri = "http://" + self.target_host + ":" + self.target_port + "/getCurrentPIDinfo?keyphrase=" + KEYPHRASE
        r = requests.get(uri)
        response = json.loads(r.text)
        self.pid = response['PID']
