import numpy as np
import scipy
import torch

import model

NX, NY = 4, 4


def xyToIdx(x: int, y: int, nx: int = NX, ny: int = NX) -> int:
    return y * nx + x


def idxToXY(idx: int, nx: int = NX, ny: int = NY) -> tuple[int, int]:
    return (idx % nx, idx // nx)


horizontal_conductance = np.array(
    [
        [0.8, 0.8, 0.8, 0],
        [0.8, 0.8, 0.8, 0],
        [0.8, 0.8, 0.8, 0],
        [0.8, 0.8, 0.8, 0],
    ]
)
vertical_conductance = np.array(
    [
        [0.8, 0.8, 0.8, 0.8],
        [0.8, 0.8, 0.8, 0.8],
        [0.8, 0.8, 0.8, 0.8],
        [0.0, 0.0, 0.0, 0.0],
    ]
)
current_load = np.array(
    [
        [0.3125e-3, 0.3125e-3, 0.3125e-3, 0.3125e-3],
        [0.3125e-3, 0.3125e-3, 0.3125e-3, 0.3125e-3],
        [0.3125e-3, 0.3125e-3, 0.3125e-3, 0.3125e-3],
        [0.3125e-3, 0.3125e-3, 0.3125e-3, 0.3125e-3],
    ]
)
candidate_points = [(x, y) for x in range(NX) for y in range(NY)]
observation_points = [(x, y) for x in range(NX) for y in range(NY)]
pad_conductance = 2.0
vdd = 1.8


# make adjacent matrix
adjacent_matrix = scipy.sparse.dok_matrix((NX * NY, NX * NY), np.float32)
for y in range(NY):
    for x in range(NX):
        idx = xyToIdx(x, y)
        for x2 in range(max(x - 1, 0), min(x + 1, NX - 1) + 1):
            if x == x2:
                continue
            idx2 = xyToIdx(x2, y)
            adjacent_matrix[idx, idx2] = horizontal_conductance[y, min(x, x2)]
        for y2 in range(max(y - 1, 0), min(y + 1, NY - 1) + 1):
            if y == y2:
                continue
            idx2 = xyToIdx(x, y2)
            adjacent_matrix[idx, idx2] = vertical_conductance[min(y, y2), x]
adjacent_matrix = adjacent_matrix.tocoo()
adjacent_matrix = torch.sparse_coo_tensor(
    np.stack([adjacent_matrix.row, adjacent_matrix.col]),
    adjacent_matrix.data,
    adjacent_matrix.shape,
    dtype=torch.float32,
)

# make current vector
current_vector = np.zeros(NX * NY)
for y in range(NY):
    for x in range(NX):
        idx = xyToIdx(x, y)
        current_vector[idx] = current_load[y, x]
current_vector = torch.tensor(current_vector, dtype=torch.float32)

# make can_index and obs_index
can_index = torch.tensor([xyToIdx(x, y) for x, y in candidate_points], dtype=torch.long)
obs_index = torch.tensor(
    [xyToIdx(x, y) for x, y in observation_points], dtype=torch.long
)

# values = torch.sparse.sum(adjacent_matrix, 1).to_dense()
# indices = torch.arange(values.size(0)).repeat(2, 1)
# D = torch.sparse_coo_tensor(indices, values, (values.size(0), values.size(0)))
# G = (D - adjacent_matrix).coalesce()
# p = torch.rand_like(can_index, dtype=torch.float32)
# x = pad_conductance * p
# g = torch.zeros_like(current_vector)
# g.scatter_(0, can_index, x)
# G_scipy = scipy.sparse.coo_matrix((G.values().numpy(), G.indices().numpy()), G.size())
# G_scipy = G_scipy + scipy.sparse.coo_matrix(
#     (g.numpy(), (can_index.numpy(), can_index.numpy())), G.size()
# )
# G_scipy = G_scipy.tocsc()
# LU_scipy = scipy.sparse.linalg.splu(G_scipy)

# train
net = model.Net(
    adjacent_matrix, current_vector, can_index, obs_index, vdd, pad_conductance
)
optimizer = torch.optim.SGD(net.parameters(), lr=0.01)
net.train()
num_epochs = 20
for i in range(num_epochs):
    loss = net()
    loss.backward()
    optimizer.step()
    result = net.getPadProbaility()
    print(result)
