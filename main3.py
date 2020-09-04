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
    t2 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave40 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t2.start()
    t3 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave41 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t3.start()
    t4 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave42 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t4.start()
    t5 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave43 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t5.start()
    t21 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave44 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t21.start()
    t6 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave45 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t6.start()
    t7 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave46 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t7.start()
    t8 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave47 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t8.start()
    t9 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave48 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t9.start()
    t10 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave49 autoport 1 masterhost 137.226.117.71 masterport 5001")
    t10.start()
    # t11 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave50 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t11.start()
    # t12 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave51 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t12.start()
    # t13 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave52 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t13.start()
    # t14 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave53 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t14.start()
    # t15 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave54 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t15.start()
    # t16 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave55 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t16.start()
    # t17 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave56 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t17.start()
    # t18 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave57 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t18.start()
    # t19 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave58 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t19.start()
    # t20 = ExecutionThread(PYTHON_PATH+" launch.py type slave conf slave59 autoport 1 masterhost 137.226.117.71 masterport 5001")
    # t20.start()
