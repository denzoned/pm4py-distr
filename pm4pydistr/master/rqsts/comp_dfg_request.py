from pm4pydistr.master.rqsts.basic_request import BasicMasterRequest
from pm4pydistr.configuration import KEYPHRASE
import requests
import os
import json

class CompDfgRequest(BasicMasterRequest):
    def __init__(self, session, target_host, target_port, use_transition, no_samples, content):
        self.slave_finished = 0
        self.session = session
        self.target_host = target_host
        self.target_port = target_port
        self.content = content
        self.use_transition = use_transition
        self.no_samples = no_samples
        BasicMasterRequest.__init__(self, None, target_host, target_port, use_transition, no_samples, content)

    def run(self):
        uri = "http://"+self.target_host+":"+self.target_port+"/sendDFG?keyphrase="+KEYPHRASE
        # Might check if it works on bigger files
        with open(self.content) as f:
            data = json.load(f)
        r = requests.post(uri, json=data)
        return r.status_code
