import networkx as nx
import numpy as np
import re
from circuit import OpBranchType, OpCircuit


def networkx_from_spice(file: str) -> nx.MultiDiGraph:
    def str_to_float(value_str: str):
        map = {
            "f": 1e-15,
            "p": 1e-12,
            "n": 1e-9,
            "u": 1e-6,
            "m": 1e-3,
            "k": 1e3,
            "meg": 1e6,
            "g": 1e9,
            "t": 1e12,
        }
        value = 1
        for k, v in map.items():
            if value_str[-len(k) :].lower() == k:
                value_str = value_str[: -len(k)]
                value = v
                break
        value *= float(value_str)
        return value

    VALUE = R"(-?\d+)(\.\d+)?((e(\+|-)?\d+)|(meg|k|m|u|n|p|f|t|g))?"
    patterns = [
        re.compile("^(R\\w+) (\\w+) (\\w+) R=({})\n".format(VALUE), re.IGNORECASE),
        re.compile("^(R\\w+) (\\w+) (\\w+) ({})\n".format(VALUE), re.IGNORECASE),
        re.compile("^(I\\w+) (\\w+) (\\w+) DC ({})".format(VALUE), re.IGNORECASE),
        re.compile("^(I\\w+) (\\w+) (\\w+) ({})".format(VALUE), re.IGNORECASE),
        re.compile("^(V\\w+) (\\w+) (\\w+) DC ({})".format(VALUE), re.IGNORECASE),
        re.compile("^(V\\w+) (\\w+) (\\w+) ({})".format(VALUE), re.IGNORECASE),
    ]
    graph = nx.MultiDiGraph()
    with open(file, "r") as f:
        for line in f:
            for p in patterns:
                match_result = p.match(line)
                if match_result is None:
                    continue
                branch_name = match_result.group(1).lower()
                node1_name = match_result.group(2).lower()
                node2_name = match_result.group(3).lower()
                value_str = match_result.group(4).lower()
                value = str_to_float(value_str)
                if not graph.has_node(node1_name):
                    graph.add_node(node1_name)
                if not graph.has_node(node2_name):
                    graph.add_node(node2_name)
                if branch_name[0].lower() == "r":
                    graph.add_edge(
                        node1_name,
                        node2_name,
                        key="g" + branch_name[1:],
                        value=1 / value,
                    )
                else:
                    graph.add_edge(node1_name, node2_name, key=branch_name, value=value)

    # remove conductance connected to ITerm
    edges_to_remove = []
    for u, v, k in graph.edges(keys=True):
        if k[0] == "g" and (
            re.search("ITerm", u, re.IGNORECASE) is not None
            or re.search("ITerm", v, re.IGNORECASE) is not None
        ):
            edges_to_remove.append((u, v, k))
    for u, v, k in edges_to_remove:
        graph.remove_edge(u, v, k)
        if re.search("ITerm", u, re.IGNORECASE) is not None:
            u, v = v, u
        for _, neighbor, key, data in list(graph.edges(v, data=True, keys=True)):
            graph.add_edge(u, neighbor, key=key, **data)
        for neighbor, _, key, data in list(graph.in_edges(v, data=True, keys=True)):
            graph.add_edge(neighbor, u, key=key, **data)
        graph.remove_node(v)

    # add additional resistor between voltage source and node
    edges_to_insert = []
    for u, v, k in graph.edges(keys=True):
        if k[0] == "v":
            edges_to_insert.append((u, v, k))
    for i, (u, v, k) in enumerate(edges_to_insert):
        # u is node, v is gnd
        x = "x_" + u
        k = "gx{}".format(i)
        graph.add_node(x)
        graph.add_edge(u, x, key=k, value=1000.0)
        for _, neighbor, key, data in list(graph.edges(u, data=True, keys=True)):
            graph.add_edge(x, neighbor, key=key, **data)
            graph.remove_edge(u, neighbor, key)
        for neighbor, _, key, data in list(graph.in_edges(u, data=True, keys=True)):
            graph.add_edge(neighbor, x, key=key, **data)
            graph.remove_edge(neighbor, u, key)

    return graph


def opcircuit_from_networkx(graph: nx.MultiDiGraph) -> OpCircuit:
    # assign number to each node
    node_id = 0
    node_map = {"0": 0}
    node_name = []
    for n in graph.nodes:
        if n == "0":
            continue
        node_map[n] = node_id
        node_id += 1
        node_name.append(n)

    # assign number to each branch
    branch_u = np.empty(graph.number_of_edges(), dtype=np.int64)
    branch_v = np.empty(graph.number_of_edges(), dtype=np.int64)
    branch_type = np.empty(graph.number_of_edges(), dtype=OpBranchType)
    branch_value = np.empty(graph.number_of_edges(), dtype=np.float32)
    branch_name = []
    for i, (u, v, k, val) in enumerate(graph.edges(keys=True, data="value")):
        branch_u[i] = node_map[u]
        branch_v[i] = node_map[v]
        if k[0] == "v":
            branch_type[i] = OpBranchType.V
        if k[0] == "i":
            branch_type[i] = OpBranchType.I
        if k[0] == "g":
            branch_type[i] = OpBranchType.G
        branch_value[i] = val
        branch_name.append(k)
    return OpCircuit(
        node_name, branch_name, branch_u, branch_v, branch_type, branch_value
    )


def get_can_index(ckt: OpCircuit):
    # mark CAN
    # all conductance connected between voltage source and node should be CAN
    can_index = []
    for i, bn in enumerate(ckt.branch_name):
        if bn[:2].lower() == "gx":
            can_index.append(i)
    return np.array(can_index, dtype=np.int64)


def get_vol_obs_index(ckt: OpCircuit):
    vol_obs_index = []
    for i, bn in enumerate(ckt.branch_name):
        if bn[0].lower() == "i":
            vol_obs_index.append(i)
    return np.array(vol_obs_index)


def get_cur_obs_index(ckt: OpCircuit):
    cur_obs_index = []
    for i, bn in enumerate(ckt.branch_name):
        if bn[0].lower() == "v":
            cur_obs_index.append(i)
    return np.array(cur_obs_index)


if __name__ == "__main__":
    file = "draft7.sp"
    graph = networkx_from_spice(file)
    ckt = opcircuit_from_networkx(graph)
    can_index = get_can_index(ckt)
    vol_obs_index = get_vol_obs_index(ckt)
    cur_obs_index = get_cur_obs_index(ckt)

    print(ckt.branch_u)
    print(ckt.branch_v)
    print(ckt.branch_type)
    print(ckt.branch_value)
