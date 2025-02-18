import networkx as nx
import scipy
import re
import numpy as np
from enum import IntEnum


class OpBranchType(IntEnum):
    V = 0
    I = 1
    G = 2


class OpCircuit(object):
    def __init__(
        self,
        node_name: list[str],
        branch_name: list[str],
        branch_u: np.ndarray,
        branch_v: np.ndarray,
        branch_type: np.ndarray,
        branch_value: np.ndarray,
    ):
        self.node_name = node_name
        self.branch_name = branch_name
        self.branch_u = branch_u
        self.branch_v = branch_v
        self.branch_type = branch_type
        self.branch_value = branch_value

        self.num_node = len(np.unique(np.r_[self.branch_u, self.branch_v]))
        self.num_voltage = np.sum(self.branch_type == OpBranchType.V)
        self.voltage_line_map = {}
        li = self.num_node - 1
        for i in np.where(self.branch_type == OpBranchType.V)[0]:
            self.voltage_line_map[i] = li
            li += 1

        # construct G J
        self.G = scipy.sparse.dok_matrix(
            (
                self.num_node + self.num_voltage - 1,
                self.num_node + self.num_voltage - 1,
            ),
            np.float32,
        )
        self.J = np.zeros(self.num_node + self.num_voltage - 1)
        for i, (u, v, t, val) in enumerate(
            zip(self.branch_u, self.branch_v, self.branch_type, self.branch_value)
        ):
            uid = u - 1
            vid = v - 1
            if t == OpBranchType.V:
                li = self.voltage_line_map[i]
                if uid > 0:
                    self.G[uid, li] = 1
                    self.G[li, uid] = 1
                if vid > 0:
                    self.G[vid, li] = -1
                    self.G[li, vid] = 1
                self.J[li] = val
            elif t == OpBranchType.I:
                if uid > 0:
                    self.J[uid] -= val
                if vid > 0:
                    self.J[vid] += val
            elif t == OpBranchType.G:
                if uid > 0:
                    self.G[uid, uid] += val
                if vid > 0:
                    self.G[vid, vid] += val
                if uid > 0 and vid > 0:
                    self.G[uid, vid] -= val
                    self.G[vid, uid] -= val
        self.V: np.ndarray = None
        self.LU: scipy.sparse.linalg.SuperLU = None

    def find_node(self, node_name: str) -> int:
        return self.node_name.index(node_name)

    def find_branch(self, branch_name: str) -> int:
        return self.branch_name.index(branch_name)

    def alter(self, index: np.ndarray, value: np.ndarray):
        for i, val in zip(index, value):
            uid = self.branch_u[i] - 1
            vid = self.branch_v[i] - 1
            t = self.branch_t[i]
            old_val = self.branch_value[i]
            if t == OpBranchType.V:
                li = self.voltage_line_map[i]
                self.J[li] = val
                self.V = None
            elif t == OpBranchType.I:
                if uid > 0:
                    self.J[uid] -= val - old_val
                if vid > 0:
                    self.J[vid] += val - old_val
                self.V = None
            elif t == OpBranchType.G:
                if uid > 0:
                    self.G[uid, uid] += val - old_val
                if vid > 0:
                    self.G[vid, vid] += val - old_val
                if uid > 0 and vid > 0:
                    self.G[uid, vid] -= val - old_val
                    self.G[vid, uid] -= val - old_val
                self.V = None
                self.LU = None
        self.branch_value[index] = value

    def solve(self) -> None:
        if self.V is not None:
            if self.LU is None:
                G_csc = scipy.sparse.csc_matrix(self.G)
                self.LU = scipy.sparse.linalg.splu(G_csc)
            self.V = self.LU.solve(self.J)

    def excitcation_index(self) -> np.ndarray:
        return np.where(
            (self.branch_type == OpBranchType.V) | (self.branch_type == OpBranchType.I)
        )[0]

    def branch_current(self, index: np.ndarray) -> np.ndarray:
        V_index_mask = self.branch_type[index] == OpBranchType.V
        V_index = index[V_index_mask]
        V_line_index = np.fromfunction(
            lambda x: self.voltage_line_map[V_index[x]],
            index.shape,
            dtype=np.int64,
        )

        V_current = self.V[V_line_index]

        I_index_mask = self.branch_type[index] == OpBranchType.I
        I_index = index[I_index_mask]
        I_current = self.branch_value[I_index]

        G_index_mask = self.branch_type[index] == OpBranchType.G
        G_index = index[G_index_mask]
        G_current = self.branch_voltage(G_index) * self.branch_value[G_index]

        current = np.zeros_like(index, dtype=np.float32)
        current[V_index_mask] = V_current
        current[G_index_mask] = G_current
        current[I_index_mask] = I_current
        return current

    def branch_voltage(self, index: np.ndarray) -> np.ndarray:
        u = self.branch_u[index] - 1
        v = self.branch_v[index] - 1
        voltage_u = np.zeros_like(index, dtype=np.float32)
        voltage_u[u > 0] = self.J[u[u > 0]]
        voltage_v = np.zeros_like(index, dtype=np.float32)
        voltage_v[v > 0] = self.J[v[v > 0]]
        return voltage_u - voltage_v
