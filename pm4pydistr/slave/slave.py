import datetime
import json
import re
import subprocess
from collections import Counter

from pm4py.algo.discovery.inductive.util.petri_el_count import Counts
from pm4py.algo.discovery.inductive.versions.dfg.util import get_tree_repr_dfg_based

from pm4pydistr.configuration import PARAMETERS_PORT, PARAMETERS_HOST, PARAMETERS_MASTER_HOST, PARAMETERS_MASTER_PORT, \
    PARAMETERS_CONF, BASE_FOLDER_LIST_OPTIONS, PARAMETERS_AUTO_HOST, PARAMETERS_AUTO_PORT, SIZE_THRESHOLD
from pm4pydistr.discovery.imd import cut_detection
from pm4pydistr.discovery.imd.detection_utils import infer_start_activities, infer_end_activities
from pm4pydistr.log_handlers.parquet import get_start_activities
from pm4pydistr.master.treecalc import SubtreeDFGBased
from pm4pydistr.configuration import PARAMETER_NO_SAMPLES, DEFAULT_MAX_NO_SAMPLES
from pm4pydistr.configuration import PARAMETER_NUM_RET_ITEMS
from pm4pydistr.configuration import PARAMETER_USE_TRANSITION, DEFAULT_USE_TRANSITION

from pm4py.algo.discovery.inductive import algorithm as inductive_miner

from pm4pydistr.slave.slave_service import SlaveSocketListener
from pm4pydistr.slave.slave_requests import SlaveRequests
from pm4pydistr.slave.variable_container import SlaveVariableContainer
from pathlib import Path
from pm4py.objects.log.importer.parquet import factory as parquet_importer
from pm4pydistr.slave.do_ms_ping import DoMasterPing
from pm4pydistr.slave.comp_dfg_rqst import CalcDfg
from pm4pydistr.slave.reserve_rqst import ReserveSlave
from pm4pydistr.slave.post_result_tree import PostResultTree
import uuid
import socket
from contextlib import closing

#import pythoncom
#import wmi
import os
from sys import platform as _platform
import shutil
import psutil

from pm4pydistr.log_handlers import parquet as parquet_handler


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


import time

from pm4py.algo.conformance.alignments.versions import dijkstra_no_heuristics, state_equation_a_star, \
    dijkstra_less_memory
from pm4py.algo.conformance.decomp_alignments.versions import recompos_maximal
from pm4py.algo.conformance.tokenreplay.versions import token_replay


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class Slave:
    def __init__(self, parameters):
        self.parameters = parameters
        self.host = socket.gethostbyaddr(socket.gethostname())[2][0]
        self.port = str(parameters[PARAMETERS_PORT])
        self.master_host = parameters[PARAMETERS_MASTER_HOST]
        self.master_port = str(parameters[PARAMETERS_MASTER_PORT])
        self.conf = parameters[PARAMETERS_CONF]
        if PARAMETERS_AUTO_HOST in parameters and parameters[PARAMETERS_AUTO_HOST] == "1":
            self.conf = str(uuid.uuid4())
            self.host = str(socket.gethostname())
        if PARAMETERS_AUTO_PORT in parameters and parameters[PARAMETERS_AUTO_PORT] == "1":
            self.port = str(find_free_port())
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

        # sleep a while before taking the slaves up :)
        time.sleep(2)

        self.slave_requests = SlaveRequests(self, self.host, self.port, self.master_host, self.master_port, self.conf)

        self.service = SlaveSocketListener(self, self.host, self.port, self.master_host, self.master_port, self.conf)
        self.service.start()

        # sleep a while before taking the slaves up :)
        time.sleep(2)

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
        if str(operatingsystem) == "2":
            import pythoncom
            import wmi
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
        if str(operatingsystem) == "0":
            # for Linux get the average temperature of all cores:
            temp = psutil.sensors_temperatures()['coretemp'][0][1]
        if str(operatingsystem) == "1":
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
        # ping = ping()
        return None

    def get_resources(self):
        self.os = self.get_OS()
        self.temp = self.get_temperature(self.os)
        self.diskusage = self.get_disk_usage()

        self.memory = self.get_memory()
        self.CPUload = self.get_load()
        self.CPUpct = self.get_CPU()
        self.iowait = self.get_iowait(self.os)
        jsonfile = {"memory": self.memory, "cpupct": self.CPUpct, "cpuload": self.CPUload, "diskusage": self.diskusage,
                    "temp": self.temp, "os": self.os, "iowait": self.iowait}
        return jsonfile

    def slave_distr(self, filename, parentfile, sendhost, sendport, local, process):
        folder = "parent_dfg"
        parentfilefolder = str(parentfile).split(".")[0]
        if os.path.exists(os.path.join(self.conf, folder, "masterdfg.json")):
            init_dfg = self.clean_init_dfg(self.conf, folder)
            if local:
                folder = os.path.join("child_dfg", process, parentfilefolder)
            print(self.conf + " cutting: " + filename + " in " + str(folder))
            if os.path.exists(os.path.join(self.conf, folder, filename)):
                with open(os.path.join(self.conf, folder, filename), "r") as read_file:
                    data = json.load(read_file)
                    print(data)
                    clean_dfg = decode_json_dfg(data["dfg"])
                    # print(clean_dfg)
                    initial_start_activities = data["initial_start"]
                    initial_end_activities = data["initial_end"]
                    process = data["process"]
                    if local:
                        session = None
                        parameters = {}
                        use_transition = str(PARAMETER_USE_TRANSITION)
                        no_samples = DEFAULT_MAX_NO_SAMPLES
                        parameters[PARAMETER_NO_SAMPLES] = no_samples
                        # start = Counter()
                        # start = infer_start_activities(clean_dfg)
                        # print("Start: " + str(start))
                        # end = infer_end_activities(clean_dfg)
                        # end = Counter()
                        # print("End: " + str(end))
                        # end = parquet_handler.get_end_activities(session, process, use_transition, no_samples)
                        # c = Counts()
                        # s = SubtreeDFGBased(clean_dfg, clean_dfg, clean_dfg, None, c, 0, 0, initial_start_activities, initial_end_activities)
                        # tree = get_tree_repr_dfg_based.get_repr(s, 0, False)
                        # tree = {"tree": str(tree)}
                        # print(str(filename) + " has the tree: " + str(tree))
                        print(clean_dfg)
                        if clean_dfg:
                            tree = inductive_miner.apply_tree_dfg(clean_dfg)
                        else:
                            tree = {"flower": data["activities"]}
                        print(tree)
                        SlaveVariableContainer.found_cuts.update({filename: {"cut": "tree", "sendhost": sendhost, "sendport": sendport, "parent": parentfile}})
                        SlaveVariableContainer.received_dfgs[filename] = tree
                        # self.send_result_tree(tree, filename, sendhost, sendport, parentfile, process)
                        print("Saving subtree: " + str(filename))
                        self.save_subtree("returned_trees", filename, str(tree), process, parentfile)
                        return tree
                    else:
                        cut = cut_detection.detect_cut(init_dfg, clean_dfg, data["name"], self.conf, data["process"],
                                                       initial_start_activities, initial_end_activities, data['activities'])
                        SlaveVariableContainer.found_cuts.update(
                            {filename: {"cut": cut, "sendhost": sendhost, "sendport": sendport, "parent": parentfile}})
                        tree = {}
                        print("Found cut for " + str(filename) + " is " + str(cut))
                        if cut == "seq" or cut == "par" or cut == "loop" or cut == "seq2":
                            print(str(self.conf) + " has to send child_dfgs for parent_dfg: " + str(filename))
                            self.send_child_dfgs(process, cut, filename)
                        if cut == "flower":
                            tree = {"flower": data["activities"]}
                            SlaveVariableContainer.received_dfgs[filename] = tree
                            # parentfile = SlaveVariableContainer.found_cuts[filename]["parent"]
                            # self.send_result_tree(tree, filename, sendhost, sendport, parentfile, process)
                            print("Saving subtree: " + str(filename))
                            self.save_subtree("returned_trees", filename, tree, process, parentfile)
                            print(tree)
                            return tree
                        if cut == "base_xor":
                            tree = {"base": data["activities"]}
                            SlaveVariableContainer.received_dfgs[filename] = tree
                            # parentfile = SlaveVariableContainer.found_cuts[filename]["parent"]
                            # self.send_result_tree(tree, filename, sendhost, sendport, parentfile, process)
                            print("Saving subtree: " + str(filename))
                            self.save_subtree("returned_trees", filename, tree, process, parentfile)
                            print(tree)
                            return tree
        print(str(filename) + " not found")
        return None

    def send_child_dfgs(self, process, cut, parent):
        threads = []
        childs = []
        tree = {cut: {}}
        parentfolder = str(parent).split(".")[0]
        processlist = {process: {}}
        sendingtime = time.time()
        if not self.checkKey(SlaveVariableContainer.send_dfgs, process):
            SlaveVariableContainer.send_dfgs.update(processlist)
        if not self.checkKey(SlaveVariableContainer.send_dfgs[process], parent):
            SlaveVariableContainer.send_dfgs[process].update({parent: {}})
        print("Send dfgs: " + str(SlaveVariableContainer.send_dfgs))
        filesizelist = {}
        for index, filename in enumerate(os.listdir(os.path.join(self.conf, "child_dfg", process, parentfolder))):
            # Best Slave Request
            # TODO sort files based on size first
            if not self.checkKey(SlaveVariableContainer.send_dfgs[process][parent], filename):
                fullfilepath = os.path.join(self.conf, "child_dfg", process, parentfolder, filename)
                file_stats = os.stat(fullfilepath)
                filesizelist[fullfilepath] = file_stats.st_size / 1024
        sortedfilesizelist = sorted(filesizelist.items(), key=lambda x: x[1], reverse=True)
        print("Sorted filesizelist: " + str(sortedfilesizelist))
        bestslave = self.slave_requests.get_best_slave()
        slavelist = self.ping_slaves(list(bestslave))
        # print("Best slaves: " + str(slavelist))
        add = 0
        for i, s in enumerate(sortedfilesizelist):
            fullfilepath = s[0]
            filename = str(s[0]).split("/")[4]
            print("Checking: " + str(fullfilepath) + " so file: " + str(filename))
            file_stats = os.stat(fullfilepath)
            print("Slave list length: " + str(len(bestslave)))
            # Size Threshold for file in KiloByte, if below do not send or first best slave is itself
            send = False
            send_file = {filename: "send"}
            if len(bestslave) > (i+add):
                if list(bestslave[i + add][1])[0] == self.conf or (file_stats.st_size / 1024) < SIZE_THRESHOLD:
                    print("Filesize below threshold or best slave is itself")
                    self.slave_distr(filename, parentfolder, self.host, self.port, True, process)
                    send = True
                    send_file = {filename: "received"}
                else:
                    # self is not best slave and file size over threshold
                    while (i + add) < len(slavelist) and not send:
                        print("Add is " + str(add) + " and i " + str(i) + " and send: " + str(send))
                        toreserve = ReserveSlave(str(slavelist[i + add][1][0]), self.master_host, self.master_port, 0)
                        print("Reserveattempt:" + str(slavelist[i + add][1][0]) + " by " + self.conf + " for file " + str(
                            fullfilepath))
                        toreserve.start()
                        toreserve.join()
                        reserveattempt = toreserve.conf
                        print("Return of reservation: " + str(reserveattempt))
                        if reserveattempt == 0:
                            besthost = slavelist[i + add][1][1]
                            bestport = slavelist[i + add][1][2]
                            print("Sending to " + str(slavelist[i + add][1][0]) + " from " + str(self.conf))
                            m = CalcDfg(self, self.conf, besthost, bestport, fullfilepath)
                            head, tail = os.path.split(fullfilepath)
                            filename = tail
                            m.start()
                            # notify master that DFG send
                            n = ReserveSlave(str(slavelist[i][1][0]), self.master_host, self.master_port, 1)
                            n.start()
                            send = True
                        else:
                            add = add + 1
            # In case all slaves are reserved, or more files than slaves, compute by itself
            if not send:
                print("No other slaves left, computing by itself")
                if parentfolder not in os.listdir(SlaveVariableContainer.conf):
                    SlaveVariableContainer.slave.create_folder(parentfolder)
                # SlaveVariableContainer.slave.load_dfg(folder, filename, json_content)
                # print(json_content)
                # SlaveVariableContainer.received_dfgs.update({filename: "notree"})
                # parent_file = json_content["parent_file"]
                self.slave_distr(filename, parent, self.host, self.port, True, process)
                send_file = {filename: "received"}
            # parent_file = str(parentfolder) + ".json"
            SlaveVariableContainer.send_dfgs[process][parent].update(send_file)
            print("send dfgs: " + str(SlaveVariableContainer.send_dfgs))
        sendingtimeb = time.time()
        timetosend = sendingtimeb - sendingtime
        print(timetosend)

    def ping_slaves(self, slave_list):
        i = 0
        bandwidth = SlaveVariableContainer.bandwidth
        # slave_list includes all information needed like from slave list in master
        ranglist = {}
        while i < len(slave_list):
            if slave_list[i][1][1] != self.host:
                print("Different host pinging")
                if self.os == 2:
                    param = "-n"
                if self.os == 0 or self.os == 1:
                    param = "-c"
                command = ['ping', param, '1', slave_list[i][1][1]]
                time_before_ping = datetime.datetime.now()
                t = subprocess.Popen(command)
                t.wait()
                time_after_ping = datetime.datetime.now()
                time_for_ping = (time_after_ping - time_before_ping).microseconds
                # We use for bandwidth a fixed variable, which is not dynamic, as it is easier and for closed environment should be more or less stable
                # In Kilobits per second
                # Delay should be 10s of microseconds, ping is in microseconds
                delay = time_for_ping / 10
                # network metric value for connecting slave
                network_metric = 256 * (pow(10, 4) / bandwidth + delay)
                ranglist.update({i: network_metric})
            if slave_list[i][1][1] == self.host:
                ranglist.update({i: 10000000000000})
            i += 1
        newlist = sorted(ranglist.items(), key=lambda x: x[1], reverse=False)
        for index, s in enumerate(newlist):
            number = index + 1
            for n in ranglist:
                if n == s[0]:
                    ranglist[n] = number

        for index, m in enumerate(slave_list):
            value = ((1 - (ranglist[index] / len(slave_list))) * SlaveVariableContainer.network_multiplier +
                     slave_list[index][1][12]) / (SlaveVariableContainer.network_multiplier + 1)
            slave_list[index][1][12] = value
        list.sort(slave_list, key=lambda x: x[1][12], reverse=True)
        return slave_list

    def save_subtree(self, folder_name, subtree_name, subtree, process, parent):
        print("Received tree " + str(subtree_name) + " for: " + str(parent))
        if not os.path.isdir(os.path.join(self.conf, folder_name)):
            os.mkdir(os.path.join(self.conf, folder_name))
        parentfile = str(parent).split(".")[0] + ".json"
        # if not os.path.exists(os.path.join(self.conf, folder_name, subtree_name)):
        #     print("Path does not exists yet")
        with open(os.path.join(self.conf, folder_name, subtree_name), "w") as write_file:
            json.dump(subtree, write_file)
            d = SlaveVariableContainer.send_dfgs
            print(d)
            if not self.checkKey(d, process):
                print("Slaveerror: Process " + process + " not found")
                return None
            elif not self.checkKey(d[process], parentfile):
                print("Slaveerror: Parent " + parentfile + " not found")
                return None
            else:
                print(self.conf + " saves received subtree " + subtree_name + " for " + parentfile)
                SlaveVariableContainer.send_dfgs[process][parentfile][subtree_name] = "received"
        print("Received dfgs: " + str(SlaveVariableContainer.send_dfgs[process][parentfile]))
        if self.check_tree(process, parentfile):
            print("After check all subtrees found for " + str(parentfile))
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
        print("Sending tree " + name + " back for parent dfg: " + res_parent)
        print("Result tree: " + str(tree) + " will be send from " + str(self.conf))
        # print("host" + host)
        # print("port" + port)
        m = PostResultTree(self, self.conf, host, port, treewithinfo)
        m.start()

    def checkKey(self, dictio, key):
        if key in dictio.keys():
            return True
        else:
            return False

    def check_tree(self, process, parent):
        d = SlaveVariableContainer.send_dfgs
        print(d)
        b = True
        if self.checkKey(d, process):
            if self.checkKey(d[process], parent):
                for s in list(d[process][parent]):
                    if d[process][parent][s] == "send":
                        b = False
                        print(str(s) + " not received yet")
        # if SlaveVariableContainer.received_dfgs[parent] == "found":
        #     print("No tree found yet for " + parent)
        #     b = False
        if b:
            print("All subtrees found for " + parent)
            SlaveVariableContainer.received_dfgs[parent] = "found"
        return b

    def result_tree(self, process, parent):
        parentfile = str(parent).split(".")[0] + ".json"
        if SlaveVariableContainer.received_dfgs[parentfile] == "found":
            tree = {SlaveVariableContainer.found_cuts[parentfile]["cut"]: {}}
            for index, filename in enumerate(os.listdir(os.path.join(self.conf, "returned_trees"))):
                # with open(os.path.join(self.conf, "returned_trees", filename), "r") as read_file:
                #     subtree = json.load(read_file)
                    # print(subtree)
                subtree = []
                for line in open(os.path.join(self.conf, "returned_trees", filename), 'r'):
                    subtree.append(json.loads(line))
                print("Tree before: " + str(tree))
                # print(SlaveVariableContainer.found_cuts[parentfile])
                # tree[SlaveVariableContainer.found_cuts[parentfile]["cut"]] = subtree
                print("Subtree for" + str(self.conf) + " is " + str(subtree) + " in file" + str(filename))
                dictkey = re.findall(r'\d+', filename)[-1]
                print(dictkey)
                tree[SlaveVariableContainer.found_cuts[parentfile]["cut"]].update({dictkey: subtree})
                print("Tree after: " + str(tree))
            return tree
        return "No tree"

    @staticmethod
    def clean_init_dfg(conf, process):
        newdfg = Counter()
        filename = "masterdfg.json"
        created = SlaveVariableContainer.slave.created
        if created:
            if os.path.exists(os.path.join(conf, process, filename)):
                with open(os.path.join(conf, process, filename), "r") as read_file:
                    dfg = json.load(read_file)
                    dfg = dfg['dfg']
                    newdfg = Counter()
                    dfglist = []
                    for s in dfg:
                        newkey = s.split("'")
                        # print(s)
                        dfgtuple = (newkey[1], newkey[3])
                        temp = [dfgtuple, 1]
                        dfglist.append(temp)
                        newdfg[dfgtuple] = 1
        else:
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


def perform_alignments(petri_string, var_list, parameters=None):
    if parameters is None:
        parameters = {}

    variant = parameters["align_variant"] if "align_variant" in parameters else "dijkstra_no_heuristics"
    parameters["ret_tuple_as_trans_desc"] = True

    if variant == "dijkstra_no_heuristics":
        return dijkstra_no_heuristics.apply_from_variants_list_petri_string(var_list, petri_string,
                                                                            parameters=parameters)
    elif variant == "state_equation_a_star":
        return state_equation_a_star.apply_from_variants_list_petri_string(var_list, petri_string,
                                                                           parameters=parameters)
    elif variant == "dijkstra_less_memory":
        return dijkstra_less_memory.apply_from_variants_list_petri_string(var_list, petri_string, parameters=parameters)
    elif variant == "recomp_maximal":
        return recompos_maximal.apply_from_variants_list_petri_string(var_list, petri_string, parameters=parameters)


def perform_token_replay(petri_string, var_list, parameters=None):
    if parameters is None:
        parameters = {}

    enable_parameters_precision = parameters[
        "enable_parameters_precision"] if "enable_parameters_precision" in parameters else False
    consider_remaining_in_fitness = parameters[
        "consider_remaining_in_fitness"] if "consider_remaining_in_fitness" in parameters else True

    parameters["return_names"] = True

    if enable_parameters_precision:
        parameters["consider_remaining_in_fitness"] = False
        parameters["try_to_reach_final_marking_through_hidden"] = False
        parameters["walk_through_hidden_trans"] = True
        parameters["stop_immediately_unfit"] = True
        parameters["consider_remaining_in_fitness"] = consider_remaining_in_fitness

    return token_replay.apply_variants_list_petri_string(var_list, petri_string, parameters=parameters)
