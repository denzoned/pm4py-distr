import json
import os

from pm4py.objects.dfg.utils.dfg_utils import get_all_activities_connected_as_input_to_activity
from pm4py.objects.dfg.utils.dfg_utils import get_all_activities_connected_as_output_to_activity
from pm4py.objects.dfg.utils.dfg_utils import get_ingoing_edges, get_outgoing_edges, get_activities_from_dfg
from pm4py.objects.dfg.utils.dfg_utils import infer_start_activities, infer_end_activities, filter_dfg_on_act
import pm4pydistr.discovery.imd.detection_utils as detection_utils
import networkx as nx

def detect_xor_cut(dfg, conn_components):
    """
    Detects XOR cut

    Parameters
    --------------
    dfg
        DFG
    conn_components:
        Connected components
    """
    if len(dfg) > 0:
        if len(conn_components) > 1:
            return [True, conn_components]

    return [False, []]


def detect_sequential_cut(dfg, strongly_connected_components):
    """
    Detect sequential cut in DFG graph

    Parameters
    --------------
    dfg
        DFG
    strongly_connected_components
        Strongly connected components
    """
    if len(strongly_connected_components) > 1:
        conn_matrix = detection_utils.get_connection_matrix(strongly_connected_components, dfg)
        comps = []
        closed = set()
        for i in range(conn_matrix.shape[0]):
            if max(conn_matrix[i, :]) == 0:
                if len(comps) == 0:
                    comps.append([])
                comps[-1].append(i)
                closed.add(i)
        cyc_continue = len(comps) >= 1
        while cyc_continue:
            cyc_continue = False
            curr_comp = []
            for i in range(conn_matrix.shape[0]):
                if i not in closed:
                    i_j = set()
                    for j in range(conn_matrix.shape[1]):
                        if conn_matrix[i][j] == 1.0:
                            i_j.add(j)
                    i_j_minus = i_j.difference(closed)
                    if len(i_j_minus) == 0:
                        curr_comp.append(i)
                        closed.add(i)
            if curr_comp:
                cyc_continue = True
                comps.append(curr_comp)
        last_cond = False
        for i in range(conn_matrix.shape[0]):
            if i not in closed:
                if not last_cond:
                    last_cond = True
                    comps.append([])
                comps[-1].append(i)
        if len(comps) > 1:
            comps = [detection_utils.perform_list_union(list(set(strongly_connected_components[i]) for i in comp)) for comp in
                     comps]
            return [True, comps]
    return [False, [], []]


def detect_loop_cut(dfg, activities, start_activities, end_activities):
    """
    Detect loop cut
    """
    all_start_activities = start_activities
    all_end_activities = list(set(end_activities).intersection(set(infer_end_activities(dfg))))

    start_activities = all_start_activities
    end_activities = list(set(all_end_activities) - set(all_start_activities))
    start_act_that_are_also_end = list(set(all_end_activities) - set(end_activities))

    do_part = []
    redo_part = []
    dangerous_redo_part = []
    exit_part = []

    for sa in start_activities:
        do_part.append(sa)
    for ea in end_activities:
        exit_part.append(ea)

    for act in activities:
        if act not in start_activities and act not in end_activities:
            input_connected_activities = get_all_activities_connected_as_input_to_activity(dfg, act)
            output_connected_activities = get_all_activities_connected_as_output_to_activity(dfg, act)
            if set(output_connected_activities).issubset(start_activities) and set(start_activities).issubset(
                    output_connected_activities):
                if len(input_connected_activities.intersection(exit_part)) > 0:
                    dangerous_redo_part.append(act)
                redo_part.append(act)
            else:
                do_part.append(act)

    if (len(do_part) + len(exit_part)) > 0 and len(redo_part) > 0:
        return [True, [do_part + exit_part, redo_part], True, len(start_act_that_are_also_end) > 0]

    return [False, [], False]


def detect_parallel_cut(this_nx_graph, strongly_connected_components, negated_ingoing, negated_outgoing, activities):
    """
    Detects parallel cut

    Parameters
    --------------
    this_nx_graph
        NX graph calculated on the DFG
    strongly_connected_components
        Strongly connected components
    negated_ingoing
        ingoing from negated DFG
    negated_outgoing
        outgoing from negated DFG
    activities
        Activities
    """
    # changed lines from original might have errors
    conn_components = detection_utils.get_connected_components(negated_ingoing, negated_outgoing, activities)

    if len(conn_components) > 1:
        conn_components = detection_utils.check_par_cut(conn_components, this_nx_graph, strongly_connected_components)

        if detection_utils.check_sa_ea_for_each_branch(conn_components):
            return [True, conn_components]

    return [False, []]

def save_cut(dfg, activities, parent_name, cut_name, position, conf, process):
    json_dfg = {}
    json_dfg.update({"dfg": dfg})
    file_name = str(parent_name) + str(cut_name) + str(position) + ".json"
    folder_name = "child_dfg"
    json_dfg.update({"name": file_name})
    json_dfg.update({"activities": activities})
    if not os.path.isdir(os.path.join(conf, process, folder_name)):
        os.mkdir(os.path.join(conf, process, folder_name))
    with open(os.path.join(conf, process, folder_name, file_name), "w") as write_file:
        json.dump(json_dfg, write_file, indent=4)
        print(file_name)
        write_file.close()

def detect_cut(dfg, parent, conf, process):
    """
    Detect generally a cut in the graph (applying all the algorithms)
    """
    if dfg:
        print('DFG will be cut')
        print(dfg)
        # Find in order: xor, seq, par, loop, seq, flower
        ingoing = get_ingoing_edges(dfg)
        outgoing = get_outgoing_edges(dfg)
        activities = get_activities_from_dfg(dfg)
        conn_components = detection_utils.get_connected_components(ingoing, outgoing, activities)

        xor_cut = detect_xor_cut(dfg, conn_components)
        if xor_cut[0]:
            found_cut = "xor"
            print(found_cut)
            for index, comp in enumerate(xor_cut[1]):
                print(comp)
                filter_dfg_on_act(dfg, comp)
                save_cut(dfg, parent, found_cut, index, conf, process)
        else:
            this_nx_graph = detection_utils.transform_dfg_to_directed_nx_graph(activities, dfg)
            strongly_connected_components = [list(x) for x in nx.strongly_connected_components(this_nx_graph)]
            seq_cut = detect_sequential_cut(dfg, strongly_connected_components)
            if seq_cut[0]:
                found_cut = "seq"
                print(found_cut)
                for index, comp in enumerate(seq_cut[1]):
                    print(comp)
                    filter_dfg = filter_dfg_on_act(dfg, comp)
                    save_cut(filter_dfg, comp, parent, found_cut, index, conf, process)
                # self.put_skips_in_seq_cut()?
            else:
                par_cut = detect_parallel_cut(this_nx_graph, strongly_connected_components, )
                if par_cut[0]:
                    found_cut = "par"
                    print(found_cut)
                    for index, comp in enumerate(par_cut[1]):
                        print(comp)
                        filtter_dfg = filter_dfg_on_act(dfg, comp)
                        save_cut(filtter_dfg, comp, parent, found_cut, index, conf, process)
                else:
                    # Do not know if start_activities really needed
                    start_activities = infer_start_activities(dfg)
                    end_activities = infer_end_activities(dfg)
                    loop_cut = detect_loop_cut(dfg, activities, start_activities, end_activities)
                    if loop_cut[0]:
                        if loop_cut[2]:
                            found_cut = "loop"
                            print(found_cut)
                            for index, comp in enumerate(loop_cut[1]):
                                print(comp)
                                filter_dfg = filter_dfg_on_act(dfg, comp)
                                save_cut(filter_dfg, comp, parent, found_cut, index, conf, process)
                                # if loop_cut[3]:
                                #   insert_skip
                        else:
                            found_cut = "seq"
                            print('seq 2')
                            # self.need_loop_on_subtree = True
                            for index, comp in enumerate(loop_cut[1]):
                                print(comp)
                                filter_dfg = filter_dfg_on_act(dfg, comp)
                                save_cut(filter_dfg, comp, parent, found_cut, index, conf, process)
                                #insert_skip
                    else:
                        pass
                    found_cut = "flower"
                    print(found_cut)
                    save_cut(dfg, comp, parent, found_cut, 0, conf, process)
        return found_cut
    else:
        return "base_xor"
