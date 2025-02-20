import numpy as np
import torch
import torch.nn as nn
import parse
import solve


file = "draft6.sp"
graph = parse.networkx_from_spice(file)
parse.process_openroad(graph)
ckt = parse.opcircuit_from_networkx(graph)
can_index = parse.get_can_index(ckt)
vol_obs_index = parse.get_vol_obs_index(ckt)
# cur_obs_index = np.array([], dtype=np.int64)
cur_obs_index = parse.get_cur_obs_index(ckt)
exc = ckt.excitcation_value()
exc_index = ckt.excitcation_index()

# weight
weight_worst_drop = float(len(vol_obs_index))
weight_total_drop = 1.0
weight_count = 1.0
gamma = 1e-7
conductance = 1000.0
vdd = 1.8

# parameters
q = nn.Parameter(torch.rand(len(can_index)))
param_list = nn.ParameterList([q])

# iterations
niters = 100

# optimizer
optimizer = torch.optim.SGD(param_list, lr=0.01)

for iter in range(niters):
    p = torch.sigmoid(q)
    can = conductance * p
    vol_obs, cur_obs = solve.OpSolveFunction.apply(
        can, can_index, exc, exc_index, vol_obs_index, cur_obs_index, ckt
    )
    ir_drop = vdd - vol_obs
    total_drop = torch.sum(ir_drop)
    worst_drop = gamma * torch.logsumexp(ir_drop / gamma, 0)
    count = torch.sum(p)
    loss = (
        weight_worst_drop * worst_drop
        + weight_total_drop * total_drop
        + weight_count * count
    )
    loss.backward()
    optimizer.step()
    print(
        "iter {}: loss {}, worst_drop {}, total_drop {}, count {}".format(
            iter, loss, torch.max(ir_drop), total_drop, count
        )
    )
