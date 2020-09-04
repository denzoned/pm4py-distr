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

if True:
    t2 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave20 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t2.start()
    t3 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave21 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t3.start()
    t4 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave22 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t4.start()
    t21 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave23 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t21.start()
    t5 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave24 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t5.start()
    t6 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave25 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t6.start()
    t7 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave26 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t7.start()
    t8 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave27 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t8.start()
    t9 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave28 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t9.start()
    t10 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave29 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t10.start()
    # t11 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave30 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t11.start()
    # t12 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave31 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t12.start()
    # t13 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave32 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t13.start()
    # t14 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave33 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t14.start()
    # t15 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave34 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t15.start()
    # t16 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave35 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t16.start()
    # t17 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave36 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t17.start()
    # t18 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave37 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t18.start()
    # t19 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave38 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t19.start()
    # t20 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave39 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t20.start()
