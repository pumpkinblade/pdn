import numpy as np
import torch


class OpSolveFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, can, can_index, exc, exc_index, vol_obs_index, cur_obs_index, ckt):
        """ "
        @brief forward
        @param ctx
        @param can the conductance value for candidate branches
        @param can_index the index for candidate branches
        @param exc the excitcation value for voltage and current branches
        @param exc_index the index for voltage and current branches
        @param vol_obs_index the index for the observed voltage
        @param cur_obs_index the index for the observed current
        """

        # update branches value
        ckt.alter(
            ckt.excitcation_index(),
            np.zeros_like(ckt.excitcation_index(), dtype=np.float32),
        )
        ckt.alter(can_index, can.numpy())
        ckt.alter(exc_index, exc)

        # solve .op
        ckt.solve()

        # retrive observation value
        vol_obs = ckt.branch_voltage(vol_obs_index)
        cur_obs = ckt.branch_current(cur_obs_index)

        ctx.can_index = can_index
        ctx.vol_obs_index = vol_obs_index
        ctx.cur_obs_index = cur_obs_index
        ctx.ckt = ckt

        return (torch.from_numpy(vol_obs), torch.from_numpy(cur_obs))

    @staticmethod
    def backward(ctx, vol_grad, cur_grad):
        """
        @brief backward
        @param ctx
        @param vol_grad the gradient for the observed voltage
        @param cur_grad the gradient for the observed current
        """

        can_index = ctx.can_index
        vol_obs_index = ctx.vol_obs_index
        cur_obs_index = ctx.cur_obs_index
        ckt = ctx.ckt

        # collect the original voltage of can branch
        origin_can_voltage = ckt.branch_voltage(can_index)

        # clear all the original excitcation
        ckt.alter(
            ckt.excitcation_index(),
            np.zeros_like(ckt.excitcation_index(), dtype=np.float32),
        )

        # set grad as excitation
        ckt.alter(vol_obs_index, vol_grad.numpy())
        ckt.alter(cur_obs_index, cur_grad.numpy())

        # compute the sensitivity
        ckt.solve()
        adjoint_can_voltage = ckt.branch_voltage(can_index)
        grad = origin_can_voltage * adjoint_can_voltage

        return (
            torch.from_numpy(grad),
            None,
            None,
            None,
            None,
            None,
            None,
        )
