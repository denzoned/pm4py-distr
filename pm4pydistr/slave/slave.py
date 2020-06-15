import json
from collections import Counter

from pm4pydistr.configuration import PARAMETERS_PORT, PARAMETERS_HOST, PARAMETERS_MASTER_HOST, PARAMETERS_MASTER_PORT, \
    PARAMETERS_CONF, BASE_FOLDER_LIST_OPTIONS, PARAMETERS_AUTO_HOST
from pm4pydistr.discovery.imd import cut_detection

from pm4pydistr.slave.slave_service import SlaveSocketListener
from pm4pydistr.slave.slave_requests import SlaveRequests
from pm4pydistr.slave.variable_container import SlaveVariableContainer
from pathlib import Path
from pm4py.objects.log.importer.parquet import factory as parquet_importer
from pm4pydistr.slave.do_ms_ping import DoMasterPing
import uuid
import socket
import pythoncom
import wmi
import os
from sys import platform as _platform
import shutil
import psutil
from pythonping import ping
from time import time


def decode_json_dfg(dfg):
    newdfg = Counter()
    for s in dfg:
        dfgtuple = (str(s[0][0]), str(s[0][1]))
        newdfg.update(dfgtuple)
        newdfg[dfgtuple] = s[1]
    newdfg = {x: count for x, count in newdfg.items() if type(x) is tuple}
    dfglist = []
    for key, value in newdfg.items():
        temp = [key, value]
        dfglist.append(temp)
    return dfglist


class Slave:
    def __init__(self, parameters):
        self.parameters = parameters
        self.host = parameters[PARAMETERS_HOST]
        self.port = str(parameters[PARAMETERS_PORT])
        self.master_host = parameters[PARAMETERS_MASTER_HOST]
        self.master_port = str(parameters[PARAMETERS_MASTER_PORT])
        self.conf = parameters[PARAMETERS_CONF]
        if PARAMETERS_AUTO_HOST in parameters and parameters[PARAMETERS_AUTO_HOST] == "1":
            # import netifaces as ni
            self.conf = str(uuid.uuid4())
            self.host = str(socket.gethostname())
            # ni.ifaddresses('eth0')
            # ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
            # self.master_host = str(ip)
        self.id = None
        self.ping_module = None
        self.pid = None
        self.memory = None
        self.CPUpct = None
        self.CPUload = None
        self.ping = None
        self.diskusage = None
        self.temp = None
        self.os = None
        self.iowait = None

        self.filters = {}
        self.dfg = {}

        if not os.path.exists(self.conf):
            os.mkdir(self.conf)

        self.slave_requests = SlaveRequests(self, self.host, self.port, self.master_host, self.master_port, self.conf)

        self.service = SlaveSocketListener(self, self.host, self.port, self.master_host, self.master_port, self.conf)
        self.service.start()

        self.slave_requests.register_to_webservice()

    def create_folder(self, folder_name):
        if not os.path.isdir(os.path.join(self.conf, folder_name)):
            os.mkdir(os.path.join(self.conf, folder_name))

    def remove_folder(self):
        # print("create folder " + str(folder_name))
        if os.path.isdir(os.path.join(self.conf)):
            shutil.rmtree(self.conf)

    def load_log(self, folder_name, log_name):
        # print("loading log " + str(log_name)+" into "+str(folder_name))
        if not os.path.exists(os.path.join(self.conf, folder_name, log_name)):
            for folder in BASE_FOLDER_LIST_OPTIONS:
                if folder_name in os.listdir(folder):
                    list_paths = parquet_importer.get_list_parquet(os.path.join(folder, folder_name))
                    list_paths_corr = {}
                    # print(list_paths)
                    for x in list_paths:
                        list_paths_corr[Path(x).name] = x
                    if log_name in list_paths_corr:
                        # print("log_name",log_name," in ",os.path.join(folder, folder_name),list_paths_corr[log_name])
                        shutil.copyfile(list_paths_corr[log_name], os.path.join(self.conf, folder_name, log_name))

    def load_dfg(self, folder_name, dfg_name, dfg):
        if not os.path.exists(os.path.join(self.conf, folder_name, dfg_name)):
            with open(os.path.join(self.conf, folder_name, dfg_name), "w") as write_file:
                json.dump(dfg, write_file)
                print("done")

    def select_dfg(self, folder_name, dfg_name, dfg):
        newdfg = {}
        if not os.path.exists(os.path.join(self.conf, folder_name, dfg_name)):
            with open(os.path.join(self.conf, folder_name, dfg_name), "r") as read_file:
                dfg = json.load(read_file)
                dfg = dfg['dfg']
                for s in dfg:
                    newkey = tuple(str(s).split('@@'))
                    newdfg[newkey] = dfg[s]
                    print(newdfg)
                    return newdfg

    def enable_ping_of_master(self):
        self.ping_module = DoMasterPing(self, self.conf, self.id, self.master_host, self.master_port, self.pid,
                                        self.host, self.port)
        self.ping_module.start()

    def get_current_PID_info(self):
        self.pid = os.getpid()
        pid = os.getpid()
        # ppid = os.getppid()
        p = psutil.Process(pid)
        # if (p.cpu_percent(interval=1)<40):
        # p.nice(10)
        return repr(p.pid)

    def get_memory(self):
        mem = psutil.virtual_memory()
        return mem

    def get_CPU(self):
        cpuuse = psutil.cpu_percent(interval=1, percpu=False)
        return cpuuse

    def get_load(self):
        cpuload = [x / psutil.cpu_count() for x in psutil.getloadavg()]
        cpuload = [x / psutil.cpu_count() for x in psutil.getloadavg()]
        # cpuload= psutil.getloadavg()
        return cpuload

    def get_iowait(self, operatingsystem):
        # TODO check if this works for Linux
        if operatingsystem == "0":
            p = psutil.Process()
            iowait = p.cpu_times()[4]
        else:
            # not possible for Windows
            iowait = 0
        return iowait

    def get_temperature(self, operatingsystem):
        if operatingsystem == "2":
            pythoncom.CoInitialize()
            # w = wmi.WMI(namespace="root\\wmi")
            # temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
            # return temperature_info.CurrentTemperature
            # return (w.MSAcpi_ThermalZoneTemperature()[0].CurrentTemperature/10.0)-273.15
            w = wmi.WMI(namespace="root\OpenHardwareMonitor")
            temperature_infos = w.Sensor()

            temp = 100
            # return temperature_infos
            for sensor in temperature_infos:
                if sensor.SensorType == u'Temperature':
                    if sensor.Name == 'CPU Package':
                        temp = sensor.Value
                        return temp
            else:
                temp = 79
                print("Start Hardwaremonitor")
                return "start Hardwaremonitor"
        else:
        # TODO placeholder for Linuxversion
            temp = 50
        return temp

    def get_OS(self):
        operatingsystem = 0
        if _platform == "linux" or _platform == "linux2":
            operatingsystem = 0
        elif _platform == "darwin":
            operatingsystem = 1
        elif _platform == "win32" or _platform == "win64":
            operatingsystem = 2
        return operatingsystem

    def get_disk_usage(self):
        disk = psutil.disk_usage('/')
        return disk

    def get_networkping(self):
        #ping = ping()
        return None

    def get_resources(self):
        self.os = self.get_OS()
        self.temp = self.get_temperature(self.os)
        self.diskusage = self.get_disk_usage()
        self.memory = self.get_memory()
        self.CPUload = self.get_load()
        self.CPUpct = self.get_CPU()
        self.iowait = self.get_iowait(self.os)
        return {"memory": self.memory, "cpupct": self.CPUpct, "cpuload": self.CPUload,
                "diskusage": self.diskusage, "temp": self.temp, "os": self.os, "iowait": self.iowait}

    def slave_distr(self, filename):
        folder = "parent_dfg"
        print("cutting:" + filename)
        if os.path.exists(os.path.join(self.conf, folder, filename)):
            with open(os.path.join(self.conf, folder, filename), "r") as read_file:
                data = json.load(read_file)
                clean_dfg = decode_json_dfg(data["dfg"])
                print(clean_dfg)
                cut = cut_detection.detect_cut(clean_dfg, data["name"], self.conf, data["process"])
                if cut == "flower":
                    tree = ', '.join([str(elem) for elem in data["activities"]])
                    tree = "X(" + tree + ", " + u'\u03c4' + ")"
                    return tree
        return None
