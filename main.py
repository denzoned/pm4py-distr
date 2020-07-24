import os
from pm4pydistr.configuration import PYTHON_PATH
from threading import Thread
import subprocess

import time

class ExecutionThread(Thread):
    def __init__(self, command):
        self.command = command
        Thread.__init__(self)

    def run(self):
        os.system(self.command)
        #proc = subprocess.Popen(self.command, shell=True)
        #pid = proc.pid

t1 = ExecutionThread(PYTHON_PATH+" launch.py type master conf master port 5001")
t1.start()
t2 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave1 autoport 1 masterhost 127.0.0.1 masterport 5001")
t2.start()
t3 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave2 autoport 1 masterhost 127.0.0.1 masterport 5001")
t3.start()
t4 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave3 autoport 1 masterhost 127.0.0.1 masterport 5001")
t4.start()
t5 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave4 autoport 1 masterhost 127.0.0.1 masterport 5001")
t5.start()
t5 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave5 autoport 1 masterhost 127.0.0.1 masterport 5001")
t5.start()
t6 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave6 autoport 1 masterhost 127.0.0.1 masterport 5001")
t6.start()
t7 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave7 autoport 1 masterhost 127.0.0.1 masterport 5001")
t7.start()
