from copy import copy
import numpy as np
import networkx as nx


def get_connected_components(ingoing, outgoing, activities):
    """
    Get connected components in the DFG graph

    Parameters
    -----------
    ingoing
        Ingoing attributes
    outgoing
        Outgoing attributes
    activities
        Activities to consider
    """
    activities_considered = set()

    connected_components = []

    for act in ingoing:
        ingoing_act = set(ingoing[act].keys())
        if act in outgoing:
            ingoing_act = ingoing_act.union(set(outgoing[act].keys()))

        ingoing_act.add(act)

        if ingoing_act not in connected_components:
            connected_components.append(ingoing_act)
            activities_considered = activities_considered.union(set(ingoing_act))

    for act in outgoing:
        if act not in ingoing:
            outgoing_act = set(outgoing[act].keys())
            outgoing_act.add(act)
            if outgoing_act not in connected_components:
                connected_components.append(outgoing_act)
            activities_considered = activities_considered.union(set(outgoing_act))

    for activ in activities:
        if activ not in activities_considered:
            added_set = set()
            added_set.add(activ)
            connected_components.append(added_set)
            activities_considered.add(activ)

    max_it = len(connected_components)
    for it in range(max_it - 1):
        something_changed = False

        old_connected_components = copy(connected_components)
        connected_components = []

        for i in range(len(old_connected_components)):
            conn1 = old_connected_components[i]

            if conn1 is not None:
                for j in range(i + 1, len(old_connected_components)):
                    conn2 = old_connected_components[j]
                    if conn2 is not None:
                        inte = conn1.intersection(conn2)

                        if len(inte) > 0:
                            conn1 = conn1.union(conn2)
                            something_changed = True
                            old_connected_components[j] = None

            if conn1 is not None and conn1 not in connected_components:
                connected_components.append(conn1)

        if not something_changed:
            break

    return connected_components


def perform_list_union(lst):
    """
    Performs the union of a list of sets

    Parameters
    ------------
    lst
        List of sets

    Returns
    ------------
    un_set
        United set
    """
    ret = set()
    for s in lst:
        ret = ret.union(s)
    return ret


def get_connection_matrix(strongly_connected_components, dfg):
    """
    Gets the connection matrix between connected components

    Parameters
    ------------
    strongly_connected_components
        Strongly connected components
    dfg
        DFG

    Returns
    ------------
    connection_matrix
        Matrix reporting the connections
    """
    act_to_scc = {}
    for index, comp in enumerate(strongly_connected_components):
        for act in comp:
            act_to_scc[act] = index
    conn_matrix = np.zeros((len(strongly_connected_components), len(strongly_connected_components)))
    for el in dfg:
        comp_el_0 = act_to_scc[el[0][0]]
        comp_el_1 = act_to_scc[el[0][1]]
        if not comp_el_0 == comp_el_1:
            conn_matrix[comp_el_1][comp_el_0] = 1
            if conn_matrix[comp_el_0][comp_el_1] == 0:
                conn_matrix[comp_el_0][comp_el_1] = -1
    return conn_matrix


def check_if_comp_is_completely_unconnected(conn1, conn2, ingoing, outgoing):
    """
    Checks if two connected components are completely unconnected each other

    Parameters
    -------------
    conn1
        First connected component
    conn2
        Second connected component
    ingoing
        Ingoing dictionary
    outgoing
        Outgoing dictionary

    Returns
    -------------
    boolean
        Boolean value that tells if the two connected components are completely unconnected
    """
    for act1 in conn1:
        for act2 in conn2:
            if ((act1 in outgoing and act2 in outgoing[act1]) and (
                    act1 in ingoing and act2 in ingoing[act1])):
                return False
    return True


def merge_connected_components(conn_components, ingoing, outgoing):
    """
    Merge the unconnected connected components

    Parameters
    -------------
    conn_components
        Connected components
    ingoing
        Ingoing dictionary
    outgoing
        Outgoing dictionary

    Returns
    -------------
    conn_components
        Merged connected components
    """
    i = 0
    while i < len(conn_components):
        conn1 = conn_components[i]
        j = i + 1
        while j < len(conn_components):
            conn2 = conn_components[j]
            if check_if_comp_is_completely_unconnected(conn1, conn2, ingoing, outgoing):
                conn_components[i] = set(conn_components[i]).union(set(conn_components[j]))
                del conn_components[j]
                continue
            j = j + 1
        i = i + 1
    return conn_components


def transform_dfg_to_directed_nx_graph(activities, dfg):
    """
    Transform DFG to directed NetworkX graph

    Parameters
    ------------
    activities
        Activities of the graph
    dfg
        DFG

    Returns
    ------------
    G
        NetworkX digraph
    nodes_map
        Correspondence between digraph nodes and activities
    """
    G = nx.DiGraph()
    for act in activities:
        G.add_node(act)
    for el in dfg:
        act1 = el[0][0]
        act2 = el[0][1]
        G.add_edge(act1, act2)
    return G


def check_par_cut(conn_components, ingoing, outgoing):
    """
    Checks if in a parallel cut all relations are present

    Parameters
    -----------
    conn_components
        Connected components
    ingoing
        Ingoing edges to activities
    outgoing
        Outgoing edges to activities
    """
    conn_components = merge_connected_components(conn_components, ingoing, outgoing)
    conn_components = sorted(conn_components, key=lambda x: len(x))
    sthing_changed = True
    while sthing_changed:
        sthing_changed = False
        i = 0
        while i < len(conn_components):
            ok_comp_idx = []
            partly_ok_comp_idx = []
            not_ok_comp_idx = []
            conn1 = conn_components[i]
            j = i + 1
            while j < len(conn_components):
                count_good = 0
                count_notgood = 0
                conn2 = conn_components[j]
                for act1 in conn1:
                    for act2 in conn2:
                        if not ((act1 in outgoing and act2 in outgoing[act1]) and (
                                act1 in ingoing and act2 in ingoing[act1])):
                            count_notgood = count_notgood + 1
                            if count_good > 0:
                                break
                        else:
                            count_good = count_good + 1
                            if count_notgood > 0:
                                break
                if count_notgood == 0:
                    ok_comp_idx.append(j)
                elif count_good > 0:
                    partly_ok_comp_idx.append(j)
                else:
                    not_ok_comp_idx.append(j)
                j = j + 1
            if not_ok_comp_idx or partly_ok_comp_idx:
                if partly_ok_comp_idx:
                    conn_components[i] = set(conn_components[i]).union(set(conn_components[partly_ok_comp_idx[0]]))
                    del conn_components[partly_ok_comp_idx[0]]
                    sthing_changed = True
                    continue
                else:
                    return False
            if sthing_changed:
                break
            i = i + 1
    if len(conn_components) > 1:
        return conn_components
    return None

def negate(dfg):
    """
    Negate relationship in the DFG graph

    Parameters
    ----------
    dfg
        Directly-Follows graph

    Returns
    ----------
    negated_dfg
        Negated Directly-Follows graph (for parallel cut detection)
    """
    negated_dfg = []

    outgoing = get_outgoing_edges(dfg)

    for el in dfg:
        if not (el[0][1] in outgoing and el[0][0] in outgoing[el[0][1]]):
            negated_dfg.append(el)

    return negated_dfg


def get_outgoing_edges(dfg):
    """
    Gets outgoing edges of the provided DFG graph
    """
    outgoing = {}
    for el in dfg:
        if type(el[0]) is str:
            if not el[0] in outgoing:
                outgoing[el[0]] = {}
            outgoing[el[0]][el[1]] = dfg[el]
        else:
            if not el[0][0] in outgoing:
                outgoing[el[0][0]] = {}
            outgoing[el[0][0]][el[0][1]] = el[1]
    return outgoing

def check_sa_ea_for_each_branch(initial_dfg, dfg, conn_components, initial_start_activities, initial_end_activities, activities):
    """
    Checks if each branch of the parallel cut has a start
    and an end node of the subgraph

    Parameters
    --------------
    conn_components
        Parallel cut

    Returns
    -------------
    boolean
        True if each branch of the parallel cut has a start and an end node
    """
    parallel_cut_sa = list(set(initial_start_activities).union(infer_start_activities_from_prev_connections_and_current_dfg(initial_dfg, dfg, activities, include_self=False)).intersection(activities))
    parallel_cut_ea = list(set(initial_end_activities).union(infer_end_activities_from_succ_connections_and_current_dfg(initial_dfg, dfg, activities, include_self=False)).intersection(activities))

    if conn_components is None:
        print("No conn_components")
        return False

    for comp in conn_components:
        comp_sa_ok = False
        comp_ea_ok = False

        for sa in parallel_cut_sa:
            print(str(sa))
            if sa in comp:
                print("comps has sa")
                comp_sa_ok = True
                break
        for ea in parallel_cut_ea:
            print(str(ea))
            if ea in comp:
                print("comps has ea")
                comp_ea_ok = True
                break

        if not (comp_sa_ok and comp_ea_ok):
            return False

    return True

def infer_start_activities_from_prev_connections_and_current_dfg(initial_dfg, dfg, activities, include_self=True):
    """
    Infer the start activities from the previous connections

    Parameters
    -----------
    initial_dfg
        Initial DFG
    dfg
        Directly-follows graph
    activities
        List of the activities contained in DFG
    """
    start_activities = set()
    for el in initial_dfg:
        if el[0][1] in activities and not el[0][0] in activities:
            start_activities.add(el[0][1])
    if include_self:
        start_activities = start_activities.union(set(infer_start_activities(dfg)))
    return start_activities


def infer_end_activities_from_succ_connections_and_current_dfg(initial_dfg, dfg, activities, include_self=True):
    """
    Infer the end activities from the previous connections

    Parameters
    -----------
    initial_dfg
        Initial DFG
    dfg
        Directly-follows graph
    activities
        List of the activities contained in DFG
    """
    end_activities = set()
    for el in initial_dfg:
        if el[0][0] in activities and not el[0][1] in activities:
            end_activities.add(el[0][0])
    if include_self:
        end_activities = end_activities.union(set(infer_end_activities(dfg)))
    return end_activities

def infer_start_activities(dfg):
    """
    Infer start activities from a Directly-Follows Graph

    Parameters
    ----------
    dfg
        Directly-Follows Graph

    Returns
    ----------
    start_activities
        Start activities in the log
    """
    ingoing = get_ingoing_edges(dfg)
    outgoing = get_outgoing_edges(dfg)

    start_activities = []

    for act in outgoing:
        if act not in ingoing:
            start_activities.append(act)

    return start_activities


def infer_end_activities(dfg):
    """
    Infer end activities from a Directly-Follows Graph

    Parameters
    ----------
    dfg
        Directly-Follows Graph

    Returns
    ----------
    end_activities
        End activities in the log
    """
    ingoing = get_ingoing_edges(dfg)
    outgoing = get_outgoing_edges(dfg)

    end_activities = []

    for act in ingoing:
        if act not in outgoing:
            end_activities.append(act)

    return end_activities

def get_outgoing_edges(dfg):
    """
    Gets outgoing edges of the provided DFG graph
    """
    outgoing = {}
    for el in dfg:
        if type(el[0]) is str:
            if not el[0] in outgoing:
                outgoing[el[0]] = {}
            outgoing[el[0]][el[1]] = dfg[el]
        else:
            if not el[0][0] in outgoing:
                outgoing[el[0][0]] = {}
            outgoing[el[0][0]][el[0][1]] = el[1]
    return outgoing


def get_ingoing_edges(dfg):
    """
    Get ingoing edges of the provided DFG graph
    """
    ingoing = {}
    for el in dfg:
        if type(el[0]) is str:
            if not el[1] in ingoing:
                ingoing[el[1]] = {}
            ingoing[el[1]][el[0]] = dfg[el]
        else:
            if not el[0][1] in ingoing:
                ingoing[el[0][1]] = {}
            ingoing[el[0][1]][el[0][0]] = el[1]
    return ingoing