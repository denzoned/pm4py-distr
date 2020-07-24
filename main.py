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
if True:
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
    t8 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave8 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t8.start()
    t9 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave9 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t9.start()
    t10 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave10 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t10.start()
    t11 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave11 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t11.start()
    t12 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave12 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t12.start()
    t13 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave13 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t13.start()
    t14 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave14 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t14.start()
    t15 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave15 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t15.start()
    t16 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave16 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t16.start()
    t17 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave17 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t17.start()
    t18 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave18 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t18.start()
    t19 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave19 autoport 1 masterhost 127.0.0.1 masterport 5001")
    t19.start()
