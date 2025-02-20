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
        node_name: np.ndarray,
        branch_name: np.ndarray,
        branch_u: np.ndarray,
        branch_v: np.ndarray,
        branch_type: np.ndarray,
        branch_value: np.ndarray,
    ):
        self.node_name = node_name
        self.branch_name = branch_name

        num_node = len(node_name)
        num_voltage = np.sum(branch_type == OpBranchType.V)
        self.voltage_line_map = {}
        li = num_node - 1
        for i in np.where(branch_type == OpBranchType.V)[0]:
            self.voltage_line_map[i] = li
            li += 1

        # construct G J
        self.J = np.zeros(num_node + num_voltage - 1)
        self.G = scipy.sparse.dok_matrix(
            (
                num_node + num_voltage - 1,
                num_node + num_voltage - 1,
            ),
            np.float32,
        )
        self.V: np.ndarray = None
        self.LU: scipy.sparse.linalg.SuperLU = None
        self.branch_u = branch_u
        self.branch_v = branch_v
        self.branch_type = branch_type
        self.branch_value = np.zeros_like(branch_value, dtype=np.float32)
        # handle voltage in Gmat
        for i in np.where(self.branch_type == OpBranchType.V)[0]:
            u = self.branch_u[i] - 1
            v = self.branch_v[i] - 1
            li = self.voltage_line_map[i]
            if u >= 0:
                self.G[u, li] = 1
                self.G[li, u] = 1
            if v >= 0:
                self.G[v, li] = -1
                self.G[li, v] = -1
        self.alter(np.arange(0, len(branch_value)), branch_value)

    def find_node(self, node_name: str) -> int:
        return self.node_name.index(node_name)

    def find_branch(self, branch_name: str) -> int:
        return self.branch_name.index(branch_name)

    def alter(self, index: np.ndarray, value: np.ndarray):
        # update voltage branch
        V_index = index[self.branch_type[index] == OpBranchType.V]
        V_value = value[self.branch_type[index] == OpBranchType.V]
        V_line_index = np.array(
            list(map(self.voltage_line_map.get, V_index)), dtype=np.int64
        )
        self.J[V_line_index] = V_value
        if len(V_line_index) > 0:
            self.V = None

        # update current branch
        I_index = index[self.branch_type[index] == OpBranchType.I]
        I_value = value[self.branch_type[index] == OpBranchType.I]
        I_u_index = self.branch_u[I_index] - 1
        I_v_index = self.branch_v[I_index] - 1
        np.subtract.at(
            self.J,
            I_u_index[I_u_index >= 0],
            I_value[I_u_index >= 0] - self.branch_value[I_index[I_u_index >= 0]],
        )
        np.add.at(
            self.J,
            I_v_index[I_v_index >= 0],
            I_value[I_v_index >= 0] - self.branch_value[I_index[I_v_index >= 0]],
        )
        if np.sum(I_u_index >= 0) + np.sum(I_v_index >= 0) > 0:
            self.V = None

        # update conductor branch
        G_index = index[self.branch_type[index] == OpBranchType.G]
        G_value = value[self.branch_type[index] == OpBranchType.G]
        G_u_index = self.branch_u[G_index] - 1
        G_u_unique, G_u_unique_inverse = np.unique(
            G_u_index[G_u_index >= 0], return_inverse=True
        )
        G_u_unique_value = np.zeros_like(G_u_unique, dtype=np.float32)
        np.add.at(
            G_u_unique_value,
            G_u_unique_inverse,
            G_value[G_u_index >= 0] - self.branch_value[G_index[G_u_index >= 0]],
        )
        self.G[G_u_unique, G_u_unique] += G_u_unique_value

        G_v_index = self.branch_v[G_index] - 1
        G_v_unique, G_v_unique_inverse = np.unique(
            G_v_index[G_v_index >= 0], return_inverse=True
        )
        G_v_unique_value = np.zeros_like(G_v_unique, dtype=np.float32)
        np.add.at(
            G_v_unique_value,
            G_v_unique_inverse,
            G_value[G_v_index >= 0] - self.branch_value[G_index[G_v_index >= 0]],
        )
        self.G[G_v_unique, G_v_unique] += G_v_unique_value

        G_uv_index = np.stack(
            [
                G_u_index[(G_u_index >= 0) & (G_v_index >= 0)],
                G_v_index[(G_u_index >= 0) & (G_v_index >= 0)],
            ]
        )
        G_uv_unique, G_uv_unique_inverse = np.unique(
            G_uv_index, axis=1, return_inverse=True
        )
        G_uv_unique_value = np.zeros(G_uv_unique.shape[1], dtype=np.float32)
        np.add.at(
            G_uv_unique_value,
            G_uv_unique_inverse,
            G_value[(G_u_index >= 0) & (G_v_index >= 0)]
            - self.branch_value[G_index[(G_u_index >= 0) & (G_v_index >= 0)]],
        )
        self.G[G_uv_unique[0], G_uv_unique[1]] -= G_uv_unique_value
        self.G[G_uv_unique[1], G_uv_unique[0]] -= G_uv_unique_value

        # for i, val in zip(index, value):
        #     uid = self.branch_u[i] - 1
        #     vid = self.branch_v[i] - 1
        #     t = self.branch_t[i]
        #     old_val = self.branch_value[i]
        #     if t == OpBranchType.V:
        #         li = self.voltage_line_map[i]
        #         self.J[li] = val
        #         self.V = None
        #     elif t == OpBranchType.I:
        #         if uid > 0:
        #             self.J[uid] -= val - old_val
        #         if vid > 0:
        #             self.J[vid] += val - old_val
        #         self.V = None
        #     elif t == OpBranchType.G:
        #         if uid > 0:
        #             self.G[uid, uid] += val - old_val
        #         if vid > 0:
        #             self.G[vid, vid] += val - old_val
        #         if uid > 0 and vid > 0:
        #             self.G[uid, vid] -= val - old_val
        #             self.G[vid, uid] -= val - old_val
        #         self.V = None
        #         self.LU = None

        self.branch_value[index] = value

    def solve(self) -> None:
        if self.V is None:
            if self.LU is None:
                G_csc = scipy.sparse.csc_matrix(self.G)
                self.LU = scipy.sparse.linalg.splu(G_csc)
            self.V = self.LU.solve(self.J)

    def excitcation_index(self) -> np.ndarray:
        return np.where(
            (self.branch_type == OpBranchType.V) | (self.branch_type == OpBranchType.I)
        )[0]

    def excitcation_value(self) -> np.ndarray:
        return self.branch_value[
            (self.branch_type == OpBranchType.V) | (self.branch_type == OpBranchType.I)
        ]

    def branch_current(self, index: np.ndarray) -> np.ndarray:
        V_index_mask = self.branch_type[index] == OpBranchType.V
        V_index = index[V_index_mask]
        V_line_index = np.array(
            list(map(lambda i: self.voltage_line_map[i], V_index)), dtype=np.int64
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
        voltage_u[u >= 0] = self.V[u[u >= 0]]
        voltage_v = np.zeros_like(index, dtype=np.float32)
        voltage_v[v >= 0] = self.V[v[v >= 0]]
        return voltage_u - voltage_v
