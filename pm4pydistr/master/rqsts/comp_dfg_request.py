from pm4pydistr.master.rqsts.basic_request import BasicMasterRequest
from pm4pydistr.configuration import KEYPHRASE
import requests
import os
import json

from pm4pydistr.master.variable_container import MasterVariableContainer


class CompDfgRequest(BasicMasterRequest):
    def __init__(self, session, target_host, target_port, use_transition, no_samples, file):
        self.slave_finished = 0
        self.session = session
        self.target_host = target_host
        self.target_port = target_port
        self.file = file
        self.use_transition = use_transition
        self.no_samples = no_samples
        self.content = None
        BasicMasterRequest.__init__(self, None, target_host, target_port, use_transition, no_samples, file)

    def run(self):
        uri = "http://"+self.target_host+":"+self.target_port+"/sendDFG?keyphrase="+KEYPHRASE + "&host=" + str("localhost") + "&port=" + str(MasterVariableContainer.master.port)
        # Might check if it works on bigger files
        with open(self.file) as f:
            data = json.load(f)
        r = requests.post(uri, json=data)
        # self.content = json.loads(r.text)
