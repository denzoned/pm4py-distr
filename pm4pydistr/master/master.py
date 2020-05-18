import math
import os
from collections import Counter
from pathlib import Path
from random import randrange
from sys import platform as _platform
from flask import jsonify

import numpy as np
import psutil
import pythoncom
import requests
import wmi
import sys
from pm4py.objects.log.importer.parquet import factory as parquet_importer
from pm4py.util import points_subset
from pm4py.algo.discovery.inductive.versions.dfg.imdfb import apply_dfg

from pm4pydistr import configuration
from pm4pydistr.configuration import DEFAULT_MAX_NO_RET_ITEMS
from pm4pydistr.configuration import KEYPHRASE
from pm4pydistr.configuration import PARAMETERS_PORT, PARAMETERS_HOST, PARAMETERS_CONF, BASE_FOLDER_LIST_OPTIONS
from pm4pydistr.master.master_service import MasterSocketListener
from pm4pydistr.master.rqsts.attr_names_req import AttributesNamesRequest
from pm4pydistr.master.rqsts.attr_values_req import AttrValuesRequest
from pm4pydistr.master.rqsts.caching_request import CachingRequest
from pm4pydistr.master.rqsts.case_duration_request import CaseDurationRequest
from pm4pydistr.master.rqsts.cases_list import CasesListRequest
from pm4pydistr.master.rqsts.comp_obj_calc_request import CompObjCalcRequest
from pm4pydistr.master.rqsts.dfg_calc_request import DfgCalcRequest
from pm4pydistr.master.rqsts.ea_request import EaRequest
from pm4pydistr.master.rqsts.events import EventsRequest
from pm4pydistr.master.rqsts.events_dotted_request import EventsDottedRequest
from pm4pydistr.master.rqsts.events_per_time_request import EventsPerTimeRequest
from pm4pydistr.master.rqsts.filter_request import FilterRequest
from pm4pydistr.master.rqsts.log_summ_request import LogSummaryRequest
from pm4pydistr.master.rqsts.master_assign_request import MasterAssignRequest
from pm4pydistr.master.rqsts.numeric_attribute_request import NumericAttributeRequest
from pm4pydistr.master.rqsts.perf_dfg_calc_request import PerfDfgCalcRequest
from pm4pydistr.master.rqsts.sa_request import SaRequest
from pm4pydistr.master.rqsts.variants import VariantsRequest
from pm4pydistr.master.session_checker import SessionChecker
from pm4pydistr.master.variable_container import MasterVariableContainer


class Master:
    def __init__(self, parameters):
        self.parameters = parameters

        self.host = parameters[PARAMETERS_HOST]
        self.port = str(parameters[PARAMETERS_PORT])
        self.conf = parameters[PARAMETERS_CONF]
        self.base_folders = BASE_FOLDER_LIST_OPTIONS

        self.sublogs_id = {}
        self.sublogs_correspondence = {}

        self.service = MasterSocketListener(self, self.port, self.conf)
        self.service.start()

        MasterVariableContainer.dbmanager.create_log_db()
        self.load_logs()

        self.slaves = {}

        self.session_checker = SessionChecker(self)
        self.session_checker.start()

        self.init_dfg = Counter()

    def load_logs(self):
        all_logs = MasterVariableContainer.dbmanager.get_logs_from_db()

        for basepath in self.base_folders:
            for folder in os.listdir(basepath):
                if folder not in self.sublogs_id:
                    self.sublogs_id[folder] = {}
                    cpath = os.path.join(basepath, folder)
                    all_parquets = parquet_importer.get_list_parquet(cpath)
                    all_parquets_basepath = [Path(x).name for x in all_parquets]

                    for name in all_parquets_basepath:
                        if name in all_logs:
                            id = all_logs[name]
                        else:
                            id = [randrange(0, 10), randrange(0, 10), randrange(0, 10), randrange(0, 10),
                                  randrange(0, 10),
                                  randrange(0, 10), randrange(0, 10)]
                            MasterVariableContainer.dbmanager.insert_log_into_db(name, id)
                        self.sublogs_id[folder][name] = id

        MasterVariableContainer.first_loading_done = True

    def do_assignment(self):
        if not MasterVariableContainer.log_assignment_done:
            all_slaves = list([eval(x) for x in self.slaves.keys()])
            for slave in all_slaves:
                self.sublogs_correspondence[str(slave)] = {}

            for folder in self.sublogs_id:
                all_logs = list(self.sublogs_id[folder])

                for slave in all_slaves:
                    self.sublogs_correspondence[str(slave)][folder] = []

                for log in all_logs:
                    distances = sorted(
                        [(x, np.linalg.norm(np.array(x) - np.array(self.sublogs_id[folder][log])), self.slaves[str(x)])
                         for x in all_slaves], key=lambda x: (x[1], x[2]))

                    self.sublogs_correspondence[str(distances[0][0])][folder].append(log)

            MasterVariableContainer.log_assignment_done = True

    def check_slaves(self):
        all_slaves = list(self.slaves.keys())

        for slave in all_slaves:
            check = False
            # if slave.get_current_PID_info() != slave:
            #    MasterVariableContainer.log_assignment_done = False
            PID1 = str(self.slaves[slave][4])
            # return PID1
            for pid2 in self.get_running_processes():
                # return str(pid2["pid"])
                if str(PID1) == str(pid2["pid"]):
                    check = True
            if check == False:
                del MasterVariableContainer.master.slaves[slave]
                MasterVariableContainer.log_assignment_done = False
                MasterVariableContainer.slave_loading_requested = False

    def make_slaves_load(self):
        if not MasterVariableContainer.slave_loading_requested:
            all_slaves = list(self.slaves.keys())

            i = 0
            while i < len(MasterVariableContainer.assign_request_threads):
                t = MasterVariableContainer.assign_request_threads[i]
                if t.slave_finished == 1:
                    del MasterVariableContainer.assign_request_threads[i]
                    continue
                i = i + 1

            for slave in all_slaves:
                slave_host = self.slaves[slave][1]
                slave_port = str(self.slaves[slave][2])

                dictio = {"logs": self.sublogs_correspondence[slave]}

                m = MasterAssignRequest(None, slave_host, slave_port, False, 100000, dictio)
                m.start()

                MasterVariableContainer.assign_request_threads.append(m)

            MasterVariableContainer.slave_loading_requested = True

    def set_filter(self, session, process, data, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = FilterRequest(session, slave_host, slave_port, use_transition, no_samples,
                              {"process": process, "data": data})
            m.start()

    def calculate_dfg(self, session, process, use_transition, no_samples, attribute_key):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = DfgCalcRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.attribute_key = attribute_key
            m.start()

            threads.append(m)

        overall_dfg = Counter()

        for thread in threads:
            thread.join()

            overall_dfg = overall_dfg + Counter(thread.content['dfg'])

        self.init_dfg = overall_dfg
        return overall_dfg

    def calculate_performance_dfg(self, session, process, use_transition, no_samples, attribute_key):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = PerfDfgCalcRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.attribute_key = attribute_key
            m.start()

            threads.append(m)

        overall_dfg = Counter()

        for thread in threads:
            thread.join()

            overall_dfg = overall_dfg + Counter(thread.content['dfg'])

        return overall_dfg

    def calculate_composite_obj(self, session, process, use_transition, no_samples, attribute_key,
                                performance_required=False):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = CompObjCalcRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.attribute_key = attribute_key
            m.performance_required = performance_required
            m.start()

            threads.append(m)

        overall_obj = {}
        overall_obj["events"] = 0
        overall_obj["cases"] = 0
        overall_obj["activities"] = Counter()
        overall_obj["start_activities"] = Counter()
        overall_obj["end_activities"] = Counter()
        overall_obj["frequency_dfg"] = Counter()
        if performance_required:
            overall_obj["performance_dfg"] = Counter()

        for thread in threads:
            thread.join()

            overall_obj["events"] = overall_obj["events"] + thread.content['obj']["events"]
            overall_obj["cases"] = overall_obj["cases"] + thread.content['obj']["cases"]
            overall_obj["activities"] = overall_obj["activities"] + Counter(thread.content['obj']["activities"])
            overall_obj["start_activities"] = overall_obj["start_activities"] + Counter(
                thread.content['obj']["start_activities"])
            overall_obj["end_activities"] = overall_obj["end_activities"] + Counter(
                thread.content['obj']["end_activities"])
            overall_obj["frequency_dfg"] = overall_obj["frequency_dfg"] + Counter(
                thread.content['obj']["frequency_dfg"])
            if performance_required:
                overall_obj["performance_dfg"] = overall_obj["performance_dfg"] + Counter(
                    thread.content['obj']["performance_dfg"])

        overall_obj["activities"] = dict(overall_obj["activities"])
        overall_obj["start_activities"] = dict(overall_obj["start_activities"])
        overall_obj["end_activities"] = dict(overall_obj["end_activities"])
        overall_obj["frequency_dfg"] = dict(overall_obj["frequency_dfg"])
        if performance_required:
            overall_obj["performance_dfg"] = dict(overall_obj["performance_dfg"])

        return overall_obj

    def get_end_activities(self, session, process, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EaRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.start()

            threads.append(m)

        overall_ea = Counter()

        for thread in threads:
            thread.join()

            overall_ea = overall_ea + Counter(thread.content['end_activities'])

        return overall_ea

    def get_start_activities(self, session, process, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = SaRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.start()

            threads.append(m)

        overall_sa = Counter()

        for thread in threads:
            thread.join()

            overall_sa = overall_sa + Counter(thread.content['start_activities'])

        return overall_sa

    def get_attribute_values(self, session, process, use_transition, no_samples, attribute_key):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = AttrValuesRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.attribute_key = attribute_key
            m.start()

            threads.append(m)

        values = Counter()

        for thread in threads:
            thread.join()

            values = values + Counter(thread.content['values'])

        return values

    def get_attributes_names(self, session, process, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = AttributesNamesRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.start()

            threads.append(m)

        names = set()

        for thread in threads:
            thread.join()

            names = names.union(set(thread.content['names']))

        return sorted(list(names))

    def get_log_summary(self, session, process, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = LogSummaryRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.start()

            threads.append(m)

        ret = {"events": 0, "cases": 0}

        for thread in threads:
            thread.join()

            ret["events"] = ret["events"] + thread.content["summary"]['events']
            ret["cases"] = ret["cases"] + thread.content["summary"]['cases']

        return ret

    def get_variants(self, session, process, use_transition, no_samples, max_ret_items=DEFAULT_MAX_NO_RET_ITEMS):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = VariantsRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items
            m.start()

            threads.append(m)

        dictio_variants = {}
        events = 0
        cases = 0

        for thread in threads:
            thread.join()

            d_variants = {x["variant"]: x for x in thread.content["variants"]}
            events = events + thread.content["events"]
            cases = cases + thread.content["cases"]

            for variant in d_variants:
                if not variant in dictio_variants:
                    dictio_variants[variant] = d_variants[variant]
                else:
                    dictio_variants[variant]["caseDuration"] = (dictio_variants[variant]["caseDuration"] *
                                                                dictio_variants[variant]["count"] + d_variants[variant][
                                                                    "caseDuration"] * d_variants[variant]["count"]) / (
                                                                       dictio_variants[variant]["count"] +
                                                                       d_variants[variant]["count"])
                    dictio_variants[variant]["count"] = dictio_variants[variant]["count"] + d_variants[variant]["count"]

            list_variants = sorted(list(dictio_variants.values()), key=lambda x: x["count"], reverse=True)
            list_variants = list_variants[:min(len(list_variants), max_ret_items)]
            dictio_variants = {x["variant"]: x for x in list_variants}

        list_variants = sorted(list(dictio_variants.values()), key=lambda x: x["count"], reverse=True)

        return {"variants": list_variants, "events": events, "cases": cases}

    def get_cases(self, session, process, use_transition, no_samples, max_ret_items=DEFAULT_MAX_NO_RET_ITEMS):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = CasesListRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items
            m.start()

            threads.append(m)

        cases_list = []
        events = 0
        cases = 0

        for thread in threads:
            thread.join()

            c_list = thread.content["cases_list"]

            cases_list = sorted(cases_list + c_list, key=lambda x: x["caseDuration"], reverse=True)
            cases_list = cases_list[:min(len(cases_list), max_ret_items)]

            events = events + thread.content["events"]
            cases = cases + thread.content["cases"]

        return {"cases_list": cases_list, "events": events, "cases": cases}

    def get_events(self, session, process, use_transition, no_samples, case_id):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EventsRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.case_id = case_id
            m.start()

            threads.append(m)

        events = []

        for thread in threads:
            thread.join()

            ev = thread.content["events"]
            if ev:
                events = ev

        return events

    def get_events_per_dotted(self, session, process, use_transition, no_samples, attribute1, attribute2, attribute3,
                              max_ret_items=10000):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EventsDottedRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items
            m.attribute1 = attribute1
            m.attribute2 = attribute2
            m.attribute3 = attribute3

            m.start()

            threads.append(m)

            break

        for thread in threads:
            thread.join()

            return thread.content

    def get_events_per_time(self, session, process, use_transition, no_samples, max_ret_items=100000):
        all_slaves = list(self.slaves.keys())

        threads = []
        points = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EventsPerTimeRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items

            m.start()

            threads.append(m)

        for thread in threads:
            thread.join()

            points = points + thread.content["points"]

        points = sorted(points)
        if len(points) > max_ret_items:
            points = points_subset.pick_chosen_points_list(max_ret_items, points)

        return points

    def get_case_duration(self, session, process, use_transition, no_samples, max_ret_items=100000):
        all_slaves = list(self.slaves.keys())

        threads = []
        points = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = CaseDurationRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items

            m.start()

            threads.append(m)

        for thread in threads:
            thread.join()

            points = points + thread.content["points"]

        points = sorted(points)
        if len(points) > max_ret_items:
            points = points_subset.pick_chosen_points_list(max_ret_items, points)

        return points

    def get_numeric_attribute_values(self, session, process, use_transition, no_samples, attribute_key,
                                     max_ret_items=100000):
        all_slaves = list(self.slaves.keys())

        threads = []
        points = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = NumericAttributeRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items
            m.attribute_key = attribute_key

            m.start()

            threads.append(m)

        for thread in threads:
            thread.join()

            points = points + thread.content["points"]

        points = sorted(points)
        if len(points) > max_ret_items:
            points = points_subset.pick_chosen_points_list(max_ret_items, points)

        return points

    def do_caching(self, session, process, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = CachingRequest(session, slave_host, slave_port, use_transition, no_samples, process)

            m.start()

            threads.append(m)

        for thread in threads:
            thread.join()

        return None

    def get_running_processes(self):
        cpu_count = 0
        infor = [p.info for p in psutil.process_iter(attrs=['pid', 'name']) if 'python.exe' in p.info['name']]
        return infor

    def get_OS(self):
        operatingsystem = ""
        if _platform == "linux" or _platform == "linux2":
            operatingsystem = "linux"
        elif _platform == "darwin":
            operatingsystem = "MAC OS X"
        elif _platform == "win32" or _platform == "win64":
            operatingsystem = "Windows"
        return operatingsystem

    def get_CPU(self):
        cpulist = psutil.cpu_percent(interval=1, percpu=False)
        return cpulist

    def get_current_PID_info(self):
        pid = os.getpid()
        ppid = os.getppid()
        p = psutil.Process(pid)
        return pid

    def get_memory(self):
        mem = psutil.virtual_memory()
        return mem

    def get_disk_usage(self):
        disk = psutil.disk_usage('/')
        return disk

    def get_netusage(self):
        net = psutil.net_connections()

    def get_temperature(self):
        pythoncom.CoInitialize()
        # w = wmi.WMI(namespace="root\\wmi")
        # temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
        # return temperature_info.CurrentTemperature
        # return (w.MSAcpi_ThermalZoneTemperature()[0].CurrentTemperature/10.0)-273.15
        w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        temperature_infos = w.Sensor()
        temp = {}
        # return temperature_infos
        for sensor in temperature_infos:
            if sensor.SensorType == u'Temperature':
                if sensor.Name == 'CPU Package':
                    temp.update({sensor.Name: sensor.Value})
                # temp.update({sensor.Name: sensor.Value})
        return temp

    def get_slaves_list2(self):
        # pid = os.getpid()
        # if not MasterVariableContainer.slave_loading_requested:
        all_slaves = list(self.slaves.keys())
        # w, h = len(all_slaves), 5
        # temporary = [[0 for x in range(h)] for y in range(w)]
        # temporary = {}

        temporary = MasterVariableContainer.master.slaves
        i = 0
        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            uri = "http://" + slave_host + ":" + slave_port + "/getcurrentPIDinfo?keyphrase=" + KEYPHRASE
            r = requests.get(uri)
            # temporary = r.json()

            # dictionary = r.json()
            # temporary[i] = MasterVariableContainer.master.slaves[slave]
            # temporary[i][4] = (dictionary["PID"])
            # i = i + 1
        return temporary

    def simple_imd(self, session, process, use_transition, no_samples, attribute):
        # get DFG
        r = self.calculate_dfg(session, process, use_transition, no_samples, attribute)
        # r = requests.get(uri)
        dfg = jsonify(r)
        start = self.get_start_activities(session, process, use_transition, no_samples)
        end = self.get_end_activities(session, process, use_transition, no_samples)
        # apply_dfg(dict(r), None, False, start, end)

        # return str(dfg)
        return dict(r)

        # apply DFG on IMD
        # apply_dfg()

    def distr_imd(self, session, process, use_transition, no_samples, attribute):
        # get DFG
        r = self.calculate_dfg(session, process, use_transition, no_samples, attribute)

        return r

    def res_ram(self, k):
        all_slaves = list(self.slaves.keys())
        print(configuration.MAX_RAM)
        for slave in all_slaves:
            slave_ram = self.slaves[slave][5][1]
            # print(slave_ram)
            slave_ram = slave_ram / configuration.MAX_RAM
            print(slave_ram)
            # resource = MasterVariableContainer.master.res_ram()
            calc = 1 / (1 + math.exp(-float(k) * ((1 - slave_ram) - 0.5)))
            print(calc)
            self.slaves[slave][11][0] = slave_ram

        return str(slave_ram)

    def res_cpu(self):
        all_slaves = list(self.slaves.keys())

        for slave in all_slaves:
            load1 = self.slaves[slave][7][0]
            load5 = self.slaves[slave][7][1]
            temp = self.slaves[slave][9]
            usage = self.slaves[slave][6]/100
            print(load1)
            if load1 > 1.1:
                hload = 0
            elif load5 != 0:
                hload = (1-load1/load5)*(1-(load1/1.1))
            else:
                hload = 1
            maxtemp = configuration.MAX_T_JUNCTION*0.8
            if maxtemp > temp:
                htemp = 1
            else:
                htemp = 0
            print(hload)
            print(usage)
            hcpu = (1-usage)**(1.1-hload)*htemp
            print(hcpu.real)
            self.slaves[slave][11][1] = hcpu.real
        return hcpu.real

    def res_disk(self):
        all_slaves = list(self.slaves.keys())

        for slave in all_slaves:
            freedisk = self.slaves[slave][8][1]
            iowait = self.slaves[slave][13]
            maxdfg = sys.getsizeof(self.init_dfg)
            print(maxdfg)
            print(freedisk)
            if freedisk > maxdfg:
                h_io = 1 - iowait
            else:
                h_io = 0
            self.slaves[slave][11][2] = h_io
        return freedisk

    def master_init(self, session, process, use_transition, no_samples, attribute_key, doall):
        # Get configuration values
        all_slaves = list(self.slaves.keys())
        configuration.MAX_RAM = 0
        for slave in all_slaves:
            ram = self.slaves[slave][5][0]
            if ram > configuration.MAX_RAM:
                configuration.MAX_RAM = ram
        MasterVariableContainer.master.check_slaves()
        MasterVariableContainer.master.do_assignment()
        MasterVariableContainer.master.make_slaves_load()
        if doall == 1:
            MasterVariableContainer.master.calculate_dfg(session, process, use_transition, no_samples,
                                                                attribute_key)
            #print(type(calc))
            #return True
        return None


