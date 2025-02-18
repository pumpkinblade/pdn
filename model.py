import torch
import torch.nn as nn

import solve


class Net(nn.Module):
    def __init__(
        self,
        adjacenet_matrix,
        current_vector,
        can_index,
        obs_index,
        vdd,
        pad_conductance,
        algorithm="direct",
        gamma=1.0,
        weight_worst_drop=1.0,
        weight_total_drop=1.0,
        weight_count=1.0,
    ):
        """
        @brief nn init
        @param adjacent_matrix the adjacent matrix for graph of the circuit
        @param current_vector the load current of each circuit node
        @param can_index the candidate node index
        @param obs_index the observation node index
        @param vdd the value of the voltage source
        @param pad_conductance the conductance of one pad
        @param algorithm one of ['direct', 'iterative']
        """

        super().__init__()

        # pad probability
        self._p = nn.Parameter(torch.randn_like(can_index, dtype=torch.float32))
        self._pad_conductance = pad_conductance
        self._opsolve = solve.OpSolve(
            adjacenet_matrix, current_vector, can_index, obs_index, vdd, algorithm
        )
        self._vdd = vdd
        self._gamma = gamma
        self._weight_worst_drop = weight_worst_drop
        self._weight_total_drop = weight_total_drop
        self._weight_count = weight_count

    def forward(self):
        """
        @brief forward
        @return obs_value the voltage value of obs
        """

        p = torch.sigmoid(self._p)
        x = self._pad_conductance * p
        y = self._opsolve(x)
        drop = self._gamma * torch.log(1 + torch.exp(self._vdd - y) / self._gamma)
        worst_drop = self._gamma * torch.logsumexp(drop / self._gamma, 0)
        total_drop = torch.sum(drop)
        count = torch.sum(p)
        return (
            self._weight_worst_drop * worst_drop
            + self._weight_total_drop * total_drop
            + self._weight_count * count
        )

    def getPadProbaility(self):
        return torch.sigmoid(self._p.clone().detach())
