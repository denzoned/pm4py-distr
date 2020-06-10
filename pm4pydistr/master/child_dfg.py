import pickle
from copy import copy
import os

from pm4pydistr.master.variable_container import MasterVariableContainer


class ChildDFG():
    def __init__(self, child_dfg, master_dfg, initial_dfg, comp, counts, rec_depth, noise_threshold,
                 initial_start_activities, initial_end_activities, cut_name, number, insert_skip, conf):
        self.dfg = copy(child_dfg)
        self.master_dfg = copy(master_dfg)
        self.initial_dfg = copy(initial_dfg)
        self.counts = counts
        self.rec_depth = rec_depth
        self.noise_threshold = noise_threshold
        self.initial_start_activities = initial_start_activities
        self.initial_end_activities = initial_end_activities
        self.cut_name = cut_name
        self.comp = comp
        self.number = number
        self.insert_skip = bool(insert_skip)
        self.conf = str(conf)
        self.create_file()


    def create_file(self):
        folder_name = "child_dfg"
        print(folder_name + " at " + self.conf)
        if not os.path.isdir(os.path.join(self.conf, folder_name)):
            os.mkdir(os.path.join(self.conf, folder_name))

        filename = str(self.rec_depth) + self.cut_name + str(self.number) + '.pickle'
        if not os.path.exists(os.path.join(self.conf, folder_name, filename)):
            with open(os.path.join(self.conf, folder_name, filename), "wb") as write_file:
                pickle.dump(self, write_file)
                print(filename + ' dumped' + '.pickle')
                write_file.close()
