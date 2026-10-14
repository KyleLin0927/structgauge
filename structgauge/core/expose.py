from __future__ import annotations
import numpy as np


def exposed_along(solid, axis, forward):
    s = np.asarray(solid, bool)
    if forward:
        s = np.flip(s, axis=axis)
    beyond = np.maximum.accumulate(s, axis=axis)
    shp = list(s.shape)
    pad = np.zeros([shp[i] if i != axis else 1 for i in range(s.ndim)], bool)
    beyond = np.concatenate(
        [pad, np.take(beyond, range(shp[axis] - 1), axis=axis)], axis=axis)
    if forward:
        beyond = np.flip(beyond, axis=axis)
    return ~beyond


def rain(solid):
    return exposed_along(solid, 1, forward=True)


def wind4(solid):
    return (exposed_along(solid, 0, True) | exposed_along(solid, 0, False)
            | exposed_along(solid, 2, True) | exposed_along(solid, 2, False))


def shielded5(solid):
    return (~rain(solid)) & (~wind4(solid))
