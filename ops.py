import networkx as nx
import numpy as np
import scipy
import torch
from enum import IntEnum
from circuit import OpBranchType, OpCircuit


class OpSolveFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, can, excitation, can_index, vol_obs_index, cur_obs_index, ckt):
        """ "
        @brief forward
        @param ctx
        @param can the value for candidate branches
        @param can_index the index for candidate branches
        @param obs_index the index for observation branches
        """

        # update branches value
        ckt.alter(can_index, can.numpy())
        exc_index = ckt.excitcation_index()
        ckt.alter(exc_index, excitation)

        # solve .op
        ckt.solve_op()

        # retrive observation value
        vol_obs = ckt.branch_voltage(vol_obs_index)
        cur_obs = ckt.branch_current(cur_obs_index)

        ctx.can_index = can_index
        ctx.vol_obs_index = vol_obs_index
        ctx.cur_obs_index = cur_obs_index
        ctx.ckt = ckt

        return (vol_obs, cur_obs)

    @staticmethod
    def backward(ctx, vol_grad, cur_grad):
        """
        @brief backward
        @param ctx
        @param grad_output the gradient for the observed voltage or current
        """

        can_index = ctx.can_index
        vol_obs_index = ctx.vol_obs_index
        cur_obs_index = ctx.cur_obs_index
        ckt = ctx.ckt

        # clear all the original excitcation
        exc_index = ckt.excitcation_index()
        ckt.alter(exc_index, np.zeros_like(exc_index, dtype=np.float32))

        # set grad as excitation
        ckt.alter(vol_obs_index, vol_grad.numpy())
        ckt.alter(cur_obs_index, cur_grad.numpy())

        # compute the sensitivity
        origin_can_voltage = ckt.branch_voltage(can_index)
        ckt.solve_op()
        adjoint_can_voltage = ckt.branch_voltage(can_index)
        grad = origin_can_voltage * adjoint_can_voltage

        return (
            torch.from_numpy(grad),
            None,
            None,
            None,
            None,
            None,
        )
