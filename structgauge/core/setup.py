from __future__ import annotations

from typing import NamedTuple

import numpy as np

from ..blocks.tables import AIR, CLIMBABLE_BLOCK_IDS, DOOR_BLOCK_IDS, NON_SOLID_BLOCK_IDS
from ..constants import DEFAULTS

PAD = 5


class Geometry(NamedTuple):
    air: np.ndarray
    solid: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    inbb: np.ndarray
    grid: np.ndarray
    doors: np.ndarray
    climbable: np.ndarray
    c: object = DEFAULTS

    @property
    def wall(self) -> np.ndarray:
        return self.solid & ~self.doors & ~self.climbable

    @property
    def scoring_region(self) -> np.ndarray:
        if self.c.doors_in_scoring_region:
            return self.inbb & (~self.solid | self.doors)
        return self.inbb & ~self.solid


def solid_mask(grid: np.ndarray) -> np.ndarray:
    m = grid != AIR
    if NON_SOLID_BLOCK_IDS:
        m &= ~np.isin(grid, list(NON_SOLID_BLOCK_IDS))
    return m


def ground_level(solid: np.ndarray) -> int:
    footprint = int(solid.any(axis=1).sum())
    thresh = max(3, int(0.02 * footprint))
    counts = solid.sum(axis=(0, 2))
    for y in range(solid.shape[1]):
        if counts[y] >= thresh:
            return y
    return int(np.argmax(counts > 0))


def prepare(ids, c=DEFAULTS, terrain=None):
    if terrain is None:
        terrain = c.virtual_terrain
    grid = np.pad(np.asarray(ids).astype(np.int16), 1)
    raw = solid_mask(grid)
    if not raw.any():
        return None

    gy = ground_level(raw) + PAD
    if terrain is True:
        gy_fill = gy
    elif terrain is False or terrain is None:
        gy_fill = 0
    else:
        gy_fill = int(terrain) + PAD
    solid = np.pad(raw, PAD, constant_values=False)
    if gy_fill > 0:
        solid[:, :gy_fill, :] = True

    doors = np.pad(np.isin(grid, list(DOOR_BLOCK_IDS)), PAD, constant_values=False)
    clim = np.pad(np.isin(grid, list(CLIMBABLE_BLOCK_IDS)), PAD, constant_values=False)
    air = (~solid) | doors | clim

    occ = np.argwhere(np.pad(grid != AIR, PAD, constant_values=False))
    if not len(occ):
        return None
    lo, hi = occ.min(0), occ.max(0)

    inbb = np.zeros(air.shape, bool)
    if c.scoring_region == "strict_interior":
        inbb[lo[0] + 1:hi[0], lo[1] + 1:hi[1], lo[2] + 1:hi[2]] = True
    elif c.scoring_region == "full_bbox":
        inbb[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1] = True
    else:
        raise ValueError(
            f"scoring_region must be 'full_bbox' or 'strict_interior'; got {c.scoring_region!r}")
    return Geometry(air, solid, lo, hi, inbb, grid, doors, clim, c)


def prepare_from_masks(occupied, solid, doors=None, climbable=None,
                       c=DEFAULTS, terrain=None):
    occupied = np.asarray(occupied, bool)
    raw = np.asarray(solid, bool)
    if not raw.any():
        return None
    doors = (np.zeros_like(raw) if doors is None else np.asarray(doors, bool))
    clim = (np.zeros_like(raw) if climbable is None else np.asarray(climbable, bool))
    if terrain is None:
        terrain = c.virtual_terrain

    gy = ground_level(raw) + PAD
    gy_fill = (gy if terrain is True
               else 0 if terrain in (False, None) else int(terrain) + PAD)
    sm = np.pad(raw, PAD, constant_values=False)
    if gy_fill > 0:
        sm[:, :gy_fill, :] = True
    dr = np.pad(doors, PAD, constant_values=False)
    cl = np.pad(clim, PAD, constant_values=False)
    air = (~sm) | dr | cl

    occ = np.argwhere(np.pad(occupied, PAD, constant_values=False))
    if not len(occ):
        return None
    lo, hi = occ.min(0), occ.max(0)
    inbb = np.zeros(air.shape, bool)
    if c.scoring_region == "strict_interior":
        inbb[lo[0] + 1:hi[0], lo[1] + 1:hi[1], lo[2] + 1:hi[2]] = True
    elif c.scoring_region == "full_bbox":
        inbb[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1] = True
    else:
        raise ValueError(f"scoring_region must be 'full_bbox' or 'strict_interior'; "
                         f"got {c.scoring_region!r}")
    return Geometry(air, sm, lo, hi, inbb,
                    np.zeros(occupied.shape, np.int16), dr, cl, c)
