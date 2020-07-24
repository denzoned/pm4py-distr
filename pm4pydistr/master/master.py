import datetime
import json
import math
import os
import time
from collections import Counter
from pathlib import Path
from random import randrange
from sys import platform as _platform
from flask import jsonify

import numpy as np
import psutil
#import pythoncom
import requests
#import wmi
import sys
import pickle
import re
from pm4py.objects.log.importer.parquet import factory as parquet_importer
from pm4py.util import points_subset
# from pm4py.algo.discovery.inductive.versions.dfg.imdfb import apply_dfg

from pm4pydistr import configuration
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
from pm4pydistr.master.rqsts.events_per_case_requests import EventsPerCaseRequest
from pm4pydistr.master.rqsts.events_per_time_request import EventsPerTimeRequest
from pm4pydistr.master.rqsts.events_per_time_first_request import EventsPerTimeFirstRequest
from pm4pydistr.master.rqsts.case_duration_request import CaseDurationRequest
from pm4pydistr.master.rqsts.numeric_attribute_request import NumericAttributeRequest
from pm4pydistr.master.rqsts.caching_request import CachingRequest
from pm4pydistr.master.rqsts.conf_align_request import AlignRequest
from pm4pydistr.master.rqsts.conf_tbr_request import TbrRequest
from pm4pydistr.master.rqsts.shutdown_request import ShutdownRequest
import math
import uuid

from pathlib import Path
from random import randrange
import os
import numpy as np
from collections import Counter
from pm4pydistr.master.session_checker import SessionChecker
from pm4pydistr.configuration import DEFAULT_WINDOW_SIZE
from pm4py.util import points_subset
from pm4py.objects.log.util import xes
import time
import sys

from pm4pydistr.master.rqsts.filter_request import FilterRequest
from pm4pydistr.master.rqsts.log_summ_request import LogSummaryRequest
from pm4pydistr.master.rqsts.master_assign_request import MasterAssignRequest
from pm4pydistr.master.rqsts.numeric_attribute_request import NumericAttributeRequest
from pm4pydistr.master.rqsts.perf_dfg_calc_request import PerfDfgCalcRequest
from pm4pydistr.master.rqsts.sa_request import SaRequest
from pm4pydistr.master.rqsts.variants import VariantsRequest
from pm4pydistr.master.session_checker import SessionChecker
from pm4pydistr.master.variable_container import MasterVariableContainer
from pm4pydistr.master.rqsts.comp_dfg_request import CompDfgRequest
from pm4pydistr.master.treecalc import SubtreeDFGBased
from pm4pydistr.master.treecalcone import SubtreeDFGBasedOne
from pm4py.algo.discovery.inductive.util.petri_el_count import Counts
from pm4py.algo.discovery.inductive.versions.dfg.util import get_tree_repr_dfg_based
from pm4pydistr.master.rqsts.rem_files_request import RemFileRequest
from pm4pydistr.discovery.imd import cut_detection
from pm4pydistr.master.rqsts.send_master_dfg import MasterDfgRequest


class Master:
    def __init__(self, parameters):
        self.parameters = parameters

        self.unique_identifier = str(uuid.uuid4())

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

        # wait that the master really comes up
        time.sleep(0.5)

        MasterVariableContainer.master_initialization_done = True
        self.init_dfg = {}
        self.imdtime = datetime

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
            print("BBBBBBBBBBBB", all_slaves)

            for folder in self.sublogs_id:
                all_logs = list(self.sublogs_id[folder])

                for slave in all_slaves:
                    self.sublogs_correspondence[str(slave)][folder] = []

                for log in all_logs:
                    distances = sorted(
                        [(x, np.linalg.norm(np.array(x) - np.array(self.sublogs_id[folder][log])), self.slaves[str(x)])
                         for x in all_slaves], key=lambda x: (x[1], x[2]))
                    print("AAAAAAAAAAAAAAAAAAAAAAAAAAA", distances, self.sublogs_correspondence)

                    self.sublogs_correspondence[str(distances[0][0])][folder].append(log)

            MasterVariableContainer.log_assignment_done = True

    def check_slaves(self):
        all_slaves = list(self.slaves.keys())

        for slave in all_slaves:
            check = False
            pid1 = str(self.slaves[slave][4])
            for pid2 in self.get_running_processes():
                # return str(pid2["pid"])
                if str(pid1) == str(pid2["pid"]):
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
                m.join()
                print(str(self.slaves[slave][0]) + ' loaded')
                MasterVariableContainer.assign_request_threads.append(m)

            MasterVariableContainer.slave_loading_requested = True

    def get_best_slave(self):
        # all_slaves = list(self.slaves.keys())
        # for slave in all_slaves:
        # if MasterVariableContainer.master.slaves[slave][12] > i:
        # MasterVariableContainer.best_slave[slave] = MasterVariableContainer.master.slaves[slave][12]
        MasterVariableContainer.best_slave = sorted(MasterVariableContainer.master.slaves.items(),
                                                    key=lambda x: x[1][12], reverse=False)
        # print(MasterVariableContainer.best_slave)

    def send_split_dfg(self, data, child):
        MasterVariableContainer.master.get_best_slave()
        slave = MasterVariableContainer.best_slave[0]
        slave_host = MasterVariableContainer.best_slave[0][1][1]
        slave_port = MasterVariableContainer.best_slave[0][1][2]
        m = CompDfgRequest(None, slave_host, slave_port, False, 100000, data)
        m.start()
        # MasterVariableContainer.assign_request_threads.append(m)
        return MasterVariableContainer.best_slave

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

        self.init_dfg.update({"dfg": dict(overall_dfg)})

        folder_name = str(process)
        if not os.path.isdir(os.path.join(self.conf, folder_name)):
            os.mkdir(os.path.join(self.conf, folder_name))
        with open(os.path.join(self.conf, folder_name, "masterdfg.json"), "w") as write_file:
            json.dump(self.init_dfg, write_file, indent=4)
        MasterVariableContainer.init_dfg_calc = True

        dfgfile = os.path.join(self.conf, folder_name, "masterdfg.json")
        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = MasterDfgRequest(None, slave_host, slave_port, False, 100000, dfgfile)
            m.start()

            threads.append(m)

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

        for el in overall_dfg:
            overall_dfg[el] = overall_dfg[el] / len(threads)

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
            for el in overall_obj["performance_dfg"]:
                overall_obj["performance_dfg"][el] = overall_obj["performance_dfg"][el] / len(threads)
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

    def get_variants(self, session, process, use_transition, no_samples, start=0, window_size=DEFAULT_WINDOW_SIZE):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = VariantsRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.window_size = window_size
            m.start_parameter = start
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
                    dictio_variants[variant]["count"] = dictio_variants[variant]["count"] + d_variants[variant]["count"]

            list_variants = sorted(list(dictio_variants.values()), key=lambda x: x["count"], reverse=True)
            list_variants = list_variants[:min(len(list_variants), window_size)]
            dictio_variants = {x["variant"]: x for x in list_variants}

        list_variants = sorted(list(dictio_variants.values()), key=lambda x: x["count"], reverse=True)

        return {"variants": list_variants, "events": events, "cases": cases}

    def get_cases(self, session, process, use_transition, no_samples, start=0, window_size=DEFAULT_WINDOW_SIZE):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = CasesListRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.window_size = window_size
            m.start_parameter = start
            m.start()

            threads.append(m)

        cases_list = []
        events = 0
        cases = 0

        for thread in threads:
            thread.join()

            c_list = thread.content["cases_list"]

            cases_list = sorted(cases_list + c_list, key=lambda x: x["caseDuration"], reverse=True)
            cases_list = cases_list[start:min(len(cases_list), window_size)]

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

    def get_events_per_case(self, session, process, use_transition, no_samples, max_ret_items=100000):
        all_slaves = list(self.slaves.keys())

        threads = []

        ret = {}

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EventsPerCaseRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items

            m.start()

            threads.append(m)

        for thread in threads:
            thread.join()

            d = thread.content["events_case"]

            for k in d:
                if not k in ret:
                    ret[k] = 0
                ret[k] = ret[k] + d[k]

        return ret

    def get_events_per_time(self, session, process, use_transition, no_samples, max_ret_items=100000,
                            timestamp_key=xes.DEFAULT_TIMESTAMP_KEY):
        all_slaves = list(self.slaves.keys())

        threads = []
        points = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EventsPerTimeRequest(session, slave_host, slave_port, use_transition, no_samples, process)
            m.max_ret_items = max_ret_items
            m.timestamp_key = timestamp_key

            m.start()

            threads.append(m)

        for thread in threads:
            thread.join()

            points = points + thread.content["points"]

        points = sorted(points)
        if len(points) > max_ret_items:
            points = points_subset.pick_chosen_points_list(max_ret_items, points)

        return points

    def get_events_per_time_first(self, session, process, use_transition, no_samples, max_ret_items=100000):
        all_slaves = list(self.slaves.keys())

        threads = []
        points = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = EventsPerTimeFirstRequest(session, slave_host, slave_port, use_transition, no_samples, process)
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

    def chunks(self, l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def perform_alignments(self, session, process, use_transition, no_samples, petri_string, var_list,
                           max_align_time=sys.maxsize, max_align_time_trace=sys.maxsize,
                           align_variant="dijkstra_no_heuristics"):
        all_slaves = list(self.slaves.keys())

        n = math.ceil(len(var_list) / len(all_slaves))
        variants_list_split = list(self.chunks(var_list, n))

        threads = []

        for index, slave in enumerate(all_slaves):
            if len(variants_list_split) > index:
                slave_host = self.slaves[slave][1]
                slave_port = str(self.slaves[slave][2])

                content = {"petri_string": petri_string, "var_list": variants_list_split[index],
                           "max_align_time": max_align_time, "max_align_time_trace": max_align_time_trace,
                           "align_variant": align_variant}

                m = AlignRequest(session, slave_host, slave_port, use_transition, no_samples, process, content)

                m.start()

                threads.append(m)

        ret_dict = {}

        for thread in threads:
            thread.join()

            ret_dict.update(thread.content["alignments"])

        return ret_dict

    def perform_tbr(self, session, process, use_transition, no_samples, petri_string, var_list,
                    enable_parameters_precision, consider_remaining_in_fitness):
        all_slaves = list(self.slaves.keys())

        n = math.ceil(len(var_list) / len(all_slaves))
        variants_list_split = list(self.chunks(var_list, n))

        threads = []

        for index, slave in enumerate(all_slaves):
            if len(variants_list_split) > index:
                slave_host = self.slaves[slave][1]
                slave_port = str(self.slaves[slave][2])

                content = {"petri_string": petri_string, "var_list": variants_list_split[index],
                           "enable_parameters_precision": enable_parameters_precision,
                           "consider_remaining_in_fitness": consider_remaining_in_fitness}

                m = TbrRequest(session, slave_host, slave_port, use_transition, no_samples, process, content)

                m.start()

                threads.append(m)

        ret_dict = []

        for thread in threads:
            thread.join()

            ret_dict = ret_dict + thread.content["tbr"]

        return ret_dict

    def perform_shutdown(self, session, process, use_transition, no_samples):
        all_slaves = list(self.slaves.keys())

        threads = []

        for slave in all_slaves:
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])

            m = ShutdownRequest(session, slave_host, slave_port, use_transition, no_samples, None)
            m.start()

            threads.append(m)

        # do shutdown
        os._exit(0)

        for thread in threads:
            thread.join()

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
        # w = wmi.WMI(namespace="root\\wmi")
        # temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
        # return temperature_info.CurrentTemperature
        # return (w.MSAcpi_ThermalZoneTemperature()[0].CurrentTemperature/10.0)-273.15
        """pythoncom.CoInitialize()
        w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        temperature_infos = w.Sensor()
        temp = {}
        # return temperature_infos
        for sensor in temperature_infos:
            if sensor.SensorType == u'Temperature':
                if sensor.Name == 'CPU Package':
                    temp.update({sensor.Name: sensor.Value})
                # temp.update({sensor.Name: sensor.Value})
        return temp"""
        return 50.0

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
        dfg = self.init_dfg
        start = self.get_start_activities(session, process, use_transition, no_samples)
        end = self.get_end_activities(session, process, use_transition, no_samples)
        clean_dfg = MasterVariableContainer.master.select_dfg(self.conf, process)
        with open(os.path.join("dfg.txt"), "w") as write_file:
            json.dump(clean_dfg, write_file)
        c = Counts()
        s = SubtreeDFGBased(clean_dfg, clean_dfg, clean_dfg, None, c, 0, 0, start, end)
        tree_repr = get_tree_repr_dfg_based.get_repr(s, 0, False)
        return tree_repr
        # apply DFG on IMD
        # apply_dfg()

    def distr_imd(self, process):
        """
        This is the initial method for the inductive miner, all slaves will receive a modified version of this,
        as the first master_dfg is different

        :param process: used Process
        :return:
        """
        if MasterVariableContainer.init_dfg_calc and os.path.exists(os.path.join(self.conf, process)):
            clean_dfg = MasterVariableContainer.master.select_dfg(MasterVariableContainer.master.conf, process)
        else:
            print("No DFG")
            return None
        self.imdtime = datetime.datetime.now()
        # cut detection
        cut = cut_detection.detect_cut(clean_dfg, clean_dfg, "m", self.conf, process, initial_start_activities=None,
                                       initial_end_activities=None, activities=None)
        MasterVariableContainer.found_cut = cut
        threads = []
        processlist = {process: {}}
        if not MasterVariableContainer.master.checkKey(MasterVariableContainer.send_dfgs, process):
            MasterVariableContainer.send_dfgs.update(processlist)
        for index, filename in enumerate(os.listdir(os.path.join(self.conf, "child_dfg", process))):
            MasterVariableContainer.master.get_best_slave()
            slave = MasterVariableContainer.best_slave[index]
            print(str(slave))
            best_host = MasterVariableContainer.best_slave[index][1][1]
            best_port = MasterVariableContainer.best_slave[index][1][2]
            # print(MasterVariableContainer.best_slave)
            fullfilepath = os.path.join(self.conf, "child_dfg", process, filename)
            # print(fullfilepath)
            m = CompDfgRequest(None, best_host, best_port, False, 100000, fullfilepath)
            threads.append(m)
            m.start()
            send_file = {filename: "send"}
            MasterVariableContainer.send_dfgs[process].update(send_file)
            m.join()
        # i = 0
        # print(len(threads))
        # for thread in threads:
        #   thread.join()
        #    tree[cut][i] = thread.content['tree']
        #    i += 1
        return None

    def checkKey(self, dictio, key):
        if key in dictio.keys():
            return True
        else:
            return False

    def check_tree(self, process):
        d = MasterVariableContainer.send_dfgs
        b = True
        if MasterVariableContainer.master.checkKey(d, process):
            for s in d[process]:
                if d[process][s] == "send":
                    b = False
        if b:
            MasterVariableContainer.tree_found = True
            endtime = datetime.datetime.now()
            self.imdtime = endtime - self.imdtime
            print("Tree computed in: " + str(self.imdtime))
        return b

    def result_tree(self, process):
        if MasterVariableContainer.tree_found:
            tree = {MasterVariableContainer.found_cut: {}, "Time to compute": str(self.imdtime)}
            for index, filename in enumerate(os.listdir(os.path.join(self.conf, "returned_trees"))):
                with open(os.path.join(self.conf, "returned_trees", filename), "r") as read_file:
                    subtree = json.load(read_file)
                    tree[MasterVariableContainer.found_cut].update(subtree)
            return tree
        return "No tree"

    def save_subtree(self, folder_name, subtree_name, subtree, process):
        if not os.path.isdir(os.path.join(self.conf, folder_name)):
            os.mkdir(os.path.join(self.conf, folder_name))
        print("Trying to save" + subtree_name)
        # if not os.path.exists(os.path.join(self.conf, folder_name, subtree_name)):
        with open(os.path.join(self.conf, folder_name, subtree_name), "w") as write_file:
            json.dump(subtree, write_file)
            d = MasterVariableContainer.send_dfgs
            if not MasterVariableContainer.master.checkKey(d, process):
                print(process + " not found on Master")
                return None
            else:
                print("Master saved " + subtree_name + " for process " + process)
                MasterVariableContainer.send_dfgs[process][subtree_name] = "received"
        if self.check_tree(process):
            self.result_tree(process)
        return None

    def res_ram(self, k):
        all_slaves = list(self.slaves.keys())
        for slave in all_slaves:
            slave_ram = self.slaves[slave][5]['available']
            slave_ram = int(slave_ram) / int(configuration.MAX_RAM)
            calc = 1 / (1 + math.exp(-float(k) * ((1 - slave_ram) - 0.5)))
            self.slaves[slave][11][0] = slave_ram

        return str(slave_ram)

    @staticmethod
    def select_dfg(conf, process):
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

    def res_cpu(self):
        all_slaves = list(self.slaves.keys())

        for slave in all_slaves:
            load1 = self.slaves[slave][7][0]
            load5 = self.slaves[slave][7][1]
            temp = self.slaves[slave][9]
            usage = self.slaves[slave][6] / 100
            if load1 > 1.1:
                hload = 0
            elif load5 != 0:
                hload = (1 - load1 / load5) * (1 - (load1 / 1.1))
            else:
                hload = 1
            maxtemp = configuration.MAX_T_JUNCTION * 0.8
            if maxtemp > temp:
                htemp = 1
            else:
                htemp = 0
            hcpu = (1 - usage) ** (1.1 - hload) * htemp
            self.slaves[slave][11][1] = hcpu.real
        return hcpu.real

    def res_disk(self):
        all_slaves = list(self.slaves.keys())
        maxdfg = sys.getsizeof(self.init_dfg)
        for slave in all_slaves:
            freedisk = self.slaves[slave][8]['free']
            iowait = self.slaves[slave][13]
            if freedisk > maxdfg:
                h_io = 1 - iowait
            else:
                h_io = 0
            self.slaves[slave][11][2] = h_io
        return freedisk

    def master_init(self, session, process, use_transition, no_samples, attribute_key, doall, clean):
        # Get configuration values
        all_slaves = list(self.slaves.keys())
        configuration.MAX_RAM = 0
        threads = []
        for slave in all_slaves:
            ram = self.slaves[slave][5]['available']
            slave_host = self.slaves[slave][1]
            slave_port = str(self.slaves[slave][2])
            if ram > configuration.MAX_RAM:
                configuration.MAX_RAM = ram
            if clean == 1:
                m = RemFileRequest(None, slave_host, slave_port, False, 100000,
                                   MasterVariableContainer.master.init_dfg)
                MasterVariableContainer.log_assignment_done = False
                MasterVariableContainer.slave_loading_requested = False
                m.start()
                m.join()
        return None

    def res_all(self, ram, cpu, disk, k):
        if MasterVariableContainer.all_resources_received:
            MasterVariableContainer.master.res_ram(k)
            MasterVariableContainer.master.res_cpu()
            MasterVariableContainer.master.res_disk()

            all_slaves = list(self.slaves.keys())
            for slave in all_slaves:
                ramval = self.slaves[slave][11][0]
                cpuval = self.slaves[slave][11][1]
                diskval = self.slaves[slave][11][2]
                f = (ram * ramval) + (cpu * cpuval) + (disk * diskval)
                f = f / (ram + cpu + disk)
                self.slaves[slave][12] = f
            # If slave in slave reservation is set on 2 reset here to 0
            for s in MasterVariableContainer.reserved_slaves:
                if MasterVariableContainer.reserved_slaves[s] == 2:
                    MasterVariableContainer.reserved_slaves[s] = 0
        return None
