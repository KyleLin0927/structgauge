from __future__ import annotations
import numpy as np
from scipy import ndimage

WALK12 = np.zeros((3, 3, 3), bool)
for _dx, _dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    for _dy in (-1, 0, 1):
        WALK12[1 + _dx, 1 + _dy, 1 + _dz] = True
WALK12[1, 1, 1] = True


def nodes(air, solid, doors, climb):
    passable = air | doors | climb
    support = solid & ~doors
    below = np.zeros_like(passable)
    below[:, 1:, :] = support[:, :-1, :]
    head = np.zeros_like(passable)
    head[:, :-1, :] = passable[:, 1:, :]
    S = (passable & head & below) | (climb & passable)
    clim_top = np.zeros_like(passable)
    clim_top[:, 1:, :] = climb[:, :-1, :]
    return S | (clim_top & passable)


def pieces(S, climb):
    lab, n = ndimage.label(S, structure=WALK12)
    if n <= 1:
        return lab, n
    parent = list(range(n + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    up = np.zeros_like(S)
    up[:, :-1, :] = S[:, 1:, :]
    ok = S & up & (climb | np.pad(climb[:, 1:, :], ((0, 0), (0, 1), (0, 0))))
    for x, y, z in np.argwhere(ok):
        a, b = find(int(lab[x, y, z])), find(int(lab[x, y + 1, z]))
        if a and b and a != b:
            parent[a] = b
    roots, remap = {}, np.zeros(n + 1, int)
    for i in range(1, n + 1):
        r = find(i)
        if r not in roots:
            roots[r] = len(roots) + 1
        remap[i] = roots[r]
    return remap[lab], len(roots)
