import numpy as np
import scipy
import torch
import torch.nn as nn


class OpSolveDirectFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, G, J, can_index, obs_index, vdd):
        """
        @brief Direct .op solver forward. (G + D(x))V = J + vddD(x), y = BV
        @param x the conductance for each candidate to connect to the voltage source
        @param G the G matrix in MNA
        @param J the J vector in MNA
        @param can_index the candidate index
        @param obs_index the observation index
        @param vdd the value of the voltage source
        """

        # solve in scipy
        g = torch.zeros_like(J)
        g.scatter_(0, can_index, x)
        G_scipy = scipy.sparse.coo_matrix(
            (G.values().numpy(), G.indices().numpy()), G.size()
        )
        G_scipy = G_scipy + scipy.sparse.coo_matrix(
            (g.numpy(), (can_index.numpy(), can_index.numpy())), G.size()
        )
        G_scipy = G_scipy.tocsc()
        J_scipy = (J + vdd * g).numpy()
        LU_scipy = scipy.sparse.linalg.splu(G_scipy)
        V_scipy = LU_scipy.solve(J_scipy)

        # retrieve y = V[obs]
        V = torch.tensor(V_scipy)
        y = V[obs_index]

        # save for backward
        ctx.LU_scipy = LU_scipy
        ctx.V = V
        ctx.can_index = can_index
        ctx.obs_index = obs_index
        ctx.vdd = vdd

        return y

    @staticmethod
    def backward(ctx, grad_output):
        """
        @brief Direct .op solver backward.
        @param grad_output
        @return grad_input
        """

        LU_scipy, V, can_index, obs_index, vdd = (
            ctx.LU_scipy,
            ctx.V,
            ctx.can_index,
            ctx.obs_index,
            ctx.vdd,
        )
        Js = torch.zeros_like(V)
        Js.scatter_(0, obs_index, -grad_output)
        Js_scipy = Js.numpy()
        Vs_scipy = LU_scipy.solve(Js_scipy)
        Vs = torch.tensor(Vs_scipy)
        return (V[can_index] - vdd) * Vs[can_index]


class OpSolveIterativeFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, A, J, can_index, obs_index, vdd):
        """
        @brief forward
        @param x conductance between candidate and voltage source
        @param A the adjacenet matrix of the circuit
        @param J the current load of each node
        @param can_index the candidate nodes
        @param obs_index the observation nodes
        @param vdd_value the value of voltage source
        @return the voltage value of obs
        """

        # iteratively solve the nodal voltage
        g = torch.zeros_like(J)
        g.scatter_(0, can_index, x)
        d = torch.sparse.sum(A, 1).to_dense() + g
        j = J + vdd * g
        V = torch.zeros(A.size(0))
        V2 = (torch.spmm(A, V) + j) / d
        while torch.dist(V, V2, 1).item() > 1e-3:
            V = V2
            V2 = (torch.spmm(A, V) + j) / d
        V = V2

        # save for backward
        ctx.A = A
        ctx.d = d
        ctx.V = V
        ctx.can_index = can_index
        ctx.obs_index = obs_index
        ctx.vdd = vdd

        return V2[obs_index]

    @staticmethod
    def backward(ctx, grad_output):
        """
        @brief backward
        @param grad_output
        @return grad_input
        """

        A, d, V, can_index, obs_index, vdd = (
            ctx.A,
            ctx.d,
            ctx.V,
            ctx.can_index,
            ctx.obs_index,
            ctx.vdd,
        )
        js = torch.zeros_like(V)
        js.scatter_(0, obs_index, -grad_output)
        Vs = torch.zeros(A.size(0))
        Vs2 = (torch.spmm(A, Vs) - js) / d
        while torch.dist(Vs, Vs2, 1).item() > 1e-3:
            Vs = Vs2
            Vs2 = (torch.spmm(A, Vs) - js) / d
        Vs = Vs2

        return (V[can_index] - vdd) * Vs[can_index], None, None, None, None, None


class OpSolve(nn.Module):
    def __init__(
        self,
        adjacent_matrix,
        current_vector,
        can_index,
        obs_index,
        vdd,
        algorithm="direct",
    ):
        """
        @brief opsolve init
        @param adjacent_matrix the adjacent matrix for graph of the circuit
        @param current_vector the load current of each circuit node
        @param can_index the candidate node index
        @param obs_index the observation node index
        @param vdd the value of the voltage source
        @param algorithm one of ['direct', 'iterative']
        """

        super().__init__()
        self._adjacent_matrix = adjacent_matrix
        self._current_vector = current_vector
        self._can_index = can_index
        self._obs_index = obs_index
        self._vdd = vdd
        self._algorithm = algorithm
        if self._algorithm == "direct":
            degree = torch.sparse.sum(self._adjacent_matrix, dim=1).to_dense()
            indices = torch.arange(degree.size(0)).repeat(2, 1)
            values = degree
            D = torch.sparse_coo_tensor(
                indices, values, (degree.size(0), degree.size(0))
            )
            self._G = (D - self._adjacent_matrix).coalesce()
            self._J = -self._current_vector
        elif self._algorithm == "iterative":
            self._A = self._adjacent_matrix
            self._J = -self._current_vector
        else:
            raise ValueError()

    def forward(self, x):
        if self._algorithm == "direct":
            return OpSolveDirectFunction.apply(
                x,
                self._G,
                self._J,
                self._can_index,
                self._obs_index,
                self._vdd,
            )
        elif self._algorithm == "iterative":
            return OpSolveIterativeFunction.apply(
                x,
                self._A,
                self._J,
                self._can_index,
                self._obs_index,
                self._vdd,
            )
        else:
            raise ValueError()


class AcDirectSolveFunction:
    @staticmethod
    def forward(ctx, x, G, can_index, obs_index):
        """
        @brief .ac solver for solving effective impedance
        @param x the conductance for each candidate to connect to the voltage source
        @param G the G matrix in MNA
        @param can_index the candidate index
        @param obs_index the observation index
        @param vdd the value of the voltage source
        """

        # solve in scipy
        g = torch.zeros(G.size(0), dtype=G.dtype)
        g.scatter_(0, can_index, x)
        G_scipy = scipy.sparse.coo_matrix(
            (G.values().numpy(), G.indices().numpy()), G.size()
        )
        G_scipy = G_scipy + scipy.sparse.coo_matrix(
            (g.numpy(), (can_index.numpy(), can_index.numpy())), G.size()
        )
        G_scipy = G_scipy.tocsc()
        J_scipy = np.zeros((G.size(0), obs_index.size(0)), dtype=G_scipy.dtype)
        for c, r in enumerate(obs_index):
            J_scipy[r, c] = 1
        LU_scipy = scipy.sparse.linalg.splu(G_scipy)
        V_scipy = LU_scipy.solve(J_scipy)

        # retrieve y = V[obs]
        V = torch.tensor(V_scipy)
        y = V[obs_index, obs_index]

        # save for backward
        ctx.y = y

        return y

    @staticmethod
    def backward(ctx, grad_output):
        """
        @brief backward
        @param grad_output
        @return grad_input
        """
        return ctx.y * ctx.y
