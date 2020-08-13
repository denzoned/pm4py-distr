import os
from pm4pydistr.configuration import PYTHON_PATH
from threading import Thread

import time

class ExecutionThread(Thread):
    def __init__(self, command):
        self.command = command
        Thread.__init__(self)

    def run(self):
        os.system(self.command)

t1 = ExecutionThread(PYTHON_PATH+" launch.py --type slave --conf slave4 --port 5005 --master-host 136.226.117.17 --master-port 5001")
t1.start()
