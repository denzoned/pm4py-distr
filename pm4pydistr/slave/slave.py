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
from pm4pydistr.slave.comp_dfg_rqst import CalcDfg
from pm4pydistr.slave.post_result_tree import PostResultTree
import uuid
import socket
import pythoncom
import wmi
import os
from sys import platform as _platform
import shutil
import psutil


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

    def select_dfg(self, folder_name, dfg_name, dfg):
        newdfg = {}
        if not os.path.exists(os.path.join(self.conf, folder_name, dfg_name)):
            with open(os.path.join(self.conf, folder_name, dfg_name), "r") as read_file:
                dfg = json.load(read_file)
                dfg = dfg['dfg']
                for s in dfg:
                    newkey = tuple(str(s).split('@@'))
                    newdfg[newkey] = dfg[s]
                    # print(newdfg)
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
        jsonfile = {"memory": self.memory, "cpupct": self.CPUpct, "cpuload": self.CPUload, "diskusage": self.diskusage, "temp": self.temp, "os": self.os, "iowait": self.iowait}
        return jsonfile

    def slave_distr(self, filename, parentfile, sendhost, sendport):
        folder = "parent_dfg"
        print("cutting:" + filename)
        if os.path.exists(os.path.join(self.conf, folder, "masterdfg.json")):
            init_dfg = self.clean_init_dfg(self.conf, folder)
            if os.path.exists(os.path.join(self.conf, folder, filename)):
                with open(os.path.join(self.conf, folder, filename), "r") as read_file:
                    data = json.load(read_file)
                    clean_dfg = decode_json_dfg(data["dfg"])
                    # print(clean_dfg)
                    initial_start_activities = data["initial_start"]
                    initial_end_activities = data["initial_end"]
                    process = data["process"]
                    cut = cut_detection.detect_cut(init_dfg, clean_dfg, data["name"], self.conf, data["process"], initial_start_activities, initial_end_activities, data['activities'])
                    SlaveVariableContainer.found_cuts.update({filename: {"cut": cut, "sendhost": sendhost, "sendport": sendport, "parent": parentfile}})
                    tree = {}
                    if cut == "seq":
                        self.send_child_dfgs(process, cut, filename)
                    if cut == "par":
                        self.send_child_dfgs(process, cut, filename)
                    if cut == "loop":
                        self.send_child_dfgs(process, cut, filename)
                    if cut == "seq2":
                        self.send_child_dfgs(process, cut, filename)
                    if cut == "flower":
                        tree = {"flower": data["activities"]}
                        SlaveVariableContainer.received_dfgs[filename] = tree
                        parentfile = SlaveVariableContainer.found_cuts[filename]["parent"]
                        self.send_result_tree(tree, filename, sendhost, sendport, parentfile, process)
                    if cut == "base_xor":
                        tree = {"base": data["activities"]}
                        SlaveVariableContainer.received_dfgs[filename] = tree
                        self.send_result_tree(tree, filename, sendhost, sendport, parentfile, process)
                    return tree
        return None

    def send_child_dfgs(self, process, cut, parent):
        threads = []
        childs = []
        tree = {cut: {}}

        processlist = {process: {}}
        if not self.checkKey(SlaveVariableContainer.send_dfgs, process):
            SlaveVariableContainer.send_dfgs.update(processlist)
        if not self.checkKey(SlaveVariableContainer.send_dfgs[process], parent):
            SlaveVariableContainer.send_dfgs[process].update({parent: {}})

        for index, filename in enumerate(os.listdir(os.path.join(self.conf, "child_dfg", process))):
            # Best Slave Request
            if not self.checkKey(SlaveVariableContainer.send_dfgs[process][parent], filename):
                fullfilepath = os.path.join(self.conf, "child_dfg", process, filename)
                bestslave = self.slave_requests.get_best_slave()
                if list(bestslave[0][1])[0] == self.conf:
                    with open(fullfilepath) as f:
                        data = json.load(f)
                    json_content = data
                    folder = "parent_dfg"
                    filename = str(json_content["name"]) + ".json"
                    if folder not in os.listdir(SlaveVariableContainer.conf):
                        SlaveVariableContainer.slave.create_folder(folder)
                    SlaveVariableContainer.slave.load_dfg(folder, filename, json_content)
                    # print(json_content)
                    SlaveVariableContainer.received_dfgs.update({filename: "notree"})
                    parent_file = json_content["parent_file"]
                    SlaveVariableContainer.slave.slave_distr(filename, parent_file, self.host, self.port)
                else:
                    # TODO ping all slaves to compute ping with resource allocation value
                    slavelist = self.ping_slaves(list(bestslave[0]))
                    besthost = slavelist[0][1]
                    bestport = slavelist[0][2]
                    m = CalcDfg(self, self.conf, besthost, bestport, fullfilepath)
                    m.start()
                send_file = {filename: "send"}
                SlaveVariableContainer.send_dfgs[process][parent].update(send_file)

    def ping_slaves(self, slave_list):
        i = 0
        bandwidth = SlaveVariableContainer.bandwidth
        # slave_list includes all information needed like from slave list in master
        while i < len(slave_list):
            ranglist = {}
            if slave_list[i][1] != self.host:
                if self.os == 2:
                    ping = os.system('ping /n 1 host')
                if self.os == 0 or self.os == 1:
                    ping = os.system('ping -c 1 host')
                # We use for bandwidth a fixed variable, which is not dynamic, as it is easier and for closed environment should be more or less stable
                # In Kilobits per second
                # Delay should be 10s of microseconds, ping is in milliseconds
                delay = ping * 100
                # network metric value for connecting slave
                network_metric = 256*(pow(10, 4)/bandwidth + delay)
                ranglist[i] = network_metric
            if slave_list[i][1] == self.host:
                ranglist[i] = 10000000000000
            i += 1
        newlist = sorted(ranglist.items(), key=lambda x: x[1], reverse=False)
        for index, s in enumerate(newlist):
            number = index + 1
            print(str(s[0]) + " " + str(number))
            for n in ranglist:
                if n == s[0]:
                    ranglist[n] = number
        print(ranglist)

        for m in slave_list:
            value = ((1-(ranglist[m]/len(slave_list))) * SlaveVariableContainer.network_multiplier + slave_list[m])/(SlaveVariableContainer.network_multiplier + 1)
            slave_list[i][12] = value
        slave_list = list.sort(slave_list, key=lambda x: x[12])
        print(slave_list)
        return slave_list

    def save_subtree(self, folder_name, subtree_name, subtree, process, parent):
        if not os.path.isdir(os.path.join(self.conf, folder_name)):
            os.mkdir(os.path.join(self.conf, folder_name))
        if not os.path.exists(os.path.join(self.conf, folder_name, subtree_name)):
            with open(os.path.join(self.conf, folder_name, subtree_name), "w") as write_file:
                json.dump(subtree, write_file)
                d = SlaveVariableContainer.send_dfgs
                parentfile = parent + ".json"
                if not self.checkKey(d, process):
                    print("Slaveerror: Process " + process + " not found")
                    return None
                if not self.checkKey(d[process], parentfile):
                    print("Slaveerror: Parent " + parentfile + " not found")
                    return None
                else:
                    print("Slave: Subtree" + subtree_name + " from " + parentfile + "received")
                    SlaveVariableContainer.send_dfgs[process][parentfile][subtree_name] = "received"
        if self.check_tree(process, parentfile):
            tree = self.result_tree(process, parent)
            host = SlaveVariableContainer.found_cuts[parentfile]["sendhost"]
            port = SlaveVariableContainer.found_cuts[parentfile]["sendport"]
            parentparent = SlaveVariableContainer.found_cuts[parentfile]["parent"]
            self.send_result_tree(tree, parentfile, host, port, parentparent, process)

    def send_result_tree(self, tree, name, host, port, res_parent, process):
        treewithinfo = {}
        treewithinfo.update({"subtree": tree})
        treewithinfo.update({"name": name})
        treewithinfo.update({"parent": res_parent})
        treewithinfo.update(({"process": process}))
        print("Tree will be send")
        print("treename:" + name)
        print("parent name: " + res_parent)
        print(tree)
        print("host" + host)
        print("port" + port)
        m = PostResultTree(self, self.conf, host, port, treewithinfo)
        m.start()

    def checkKey(self, dictio, key):
        if key in dictio.keys():
            return True
        else:
            return False

    def check_tree(self, process, parent):
        d = SlaveVariableContainer.send_dfgs
        b = True
        if self.checkKey(d, process):
            if self.checkKey(d[process], parent):
                for s in d[process][parent]:
                    if d[process][parent][s] == "send":
                        b = False
        if SlaveVariableContainer.received_dfgs[parent] == "found":
            b = False
        if b:
            print("Parent " + parent + " tree found")
            SlaveVariableContainer.received_dfgs[parent] = "found"
        return b

    def result_tree(self, process, parent):
        parentfile = parent + ".json"
        if SlaveVariableContainer.received_dfgs[parentfile] == "found":
            tree = {SlaveVariableContainer.found_cuts[parentfile]["cut"]: {}}
            for index, filename in enumerate(os.listdir(os.path.join(self.conf, "returned_tree"))):
                with open(os.path.join(self.conf, "returned_tree", filename), "r") as read_file:
                    subtree = json.load(read_file)
                    tree[SlaveVariableContainer.found_cuts[parentfile]["cut"]].update(subtree)
            return tree
        return "No tree"

    @staticmethod
    def clean_init_dfg(conf, process):
        newdfg = Counter()
        filename = "masterdfg.json"
        if os.path.exists(os.path.join(conf, process, filename)):
            with open(os.path.join(conf, process, filename), "r") as read_file:
                dfg = json.load(read_file)
                dfg = dfg['dfg']
                for s in dfg:
                    newkey = s.split('@@')
                    # x = re.search("T[0-9]", newkey[0])
                    # if x:
                    #    newkey[0] = newkey[0].split(' ', 1)[1]
                    # x1 = re.search("T[0-9]", newkey[1])
                    # if x1:
                    #    newkey[1] = newkey[1].split(' ', 1)[1]
                    dfgtuple = (str(newkey[0]), str(newkey[1]))
                    newdfg.update(dfgtuple)
                    newdfg[dfgtuple] = dfg[s]
                newdfg = {x: count for x, count in newdfg.items() if type(x) is tuple}
                dfglist = []
                for key, value in newdfg.items():
                    temp = [key, value]
                    dfglist.append(temp)
            # print(dfglist)
        return dfglist