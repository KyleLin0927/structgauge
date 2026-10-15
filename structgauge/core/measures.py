from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


import numpy as np
from ..constants import DEFAULTS


@dataclass(frozen=True)
class Measures:
    shelter: Optional[float] = None
    access: Optional[float] = None
    intermediates: dict = field(default_factory=dict)

    def __repr__(self):
        f = lambda v: "None" if v is None else "%.4f" % v
        return "Measures(shelter=%s, access=%s)" % (f(self.shelter), f(self.access))


def _setup(ids, c=DEFAULTS):
    from . import setup as SU
    return SU.prepare(ids, c)


def _align_off(air_shape, grid_shape, raw_shape, xyz, dom):
    cands = [(np.array(air_shape) - np.array(grid_shape)) // 2,
             (np.array(air_shape) - np.array(raw_shape)) // 2]
    best, bcov = None, -1.0
    dl = len(dom) or 1
    for o in cands:
        cov = len(set(map(tuple, xyz + o)) & dom) / dl
        if cov > bcov:
            best, bcov = o, cov
    if bcov < 0.95:
        raise RuntimeError(f"coordinate frame mismatch: best coverage is only {bcov:.1%} (both candidate frames tried)")
    return best, bcov


def shelter_from_field(ids, xyz, omega_raw, c=DEFAULTS, geo=None):
    st = geo if geo is not None else _setup(ids, c)
    if st is None:
        return None, {"reason": "no solid blocks"}
    air, sm, lo, hi, inbb, grid, doors, clim = st[:8]
    if geo is not None:
        off = np.zeros(3, int)
    else:
        dom = set(map(tuple, np.argwhere(inbb & ~sm)))
        if not dom:
            if c.access_min_nodes == 0:
                return 0.0, {"shelter_zero_annotated": "no interior cells: both measures are 0 by convention"}
            return None, {"reason": "no interior cells (fully solid)"}
        off, _ = _align_off(air.shape, grid.shape,
                            np.asarray(ids).shape, xyz, dom)
    idx = xyz + off
    ok = ((idx >= 0).all(1) & (idx < np.array(air.shape)).all(1))
    idx = idx[ok]
    vn = omega_raw[ok] * (1.0 - c.gamma)
    mass = float(vn.sum())
    inter = {"omega_mass": mass, "n_scored_cells": int(ok.sum())}
    if mass <= 0:
        if c.access_min_nodes == 0:
            inter["shelter_zero_annotated"] = "zero omega mass: both measures are 0 by convention"
            return 0.0, inter
        return None, inter
    from . import expose as EXP
    e_rain = EXP.rain(sm)
    e_wind = EXP.wind4(sm)
    er = e_rain[idx[:, 0], idx[:, 1], idx[:, 2]]
    ew = e_wind[idx[:, 0], idx[:, 1], idx[:, 2]]
    inter["shelter_rain"] = round(float(vn[~er].sum() / mass), 4)
    inter["shelter_wind"] = round(float(vn[~ew].sum() / mass), 4)
    inter["saturated_mass_frac"] = round(
        float(vn[omega_raw[ok] * (1.0 - c.gamma) > 0.99].sum() / mass), 4)
    return round(float(vn[(~er) & (~ew)].sum() / mass), 4), inter


def access_from_field(ids, xyz, omega_raw, c=DEFAULTS, geo=None):
    from . import walk as WK
    st = geo if geo is not None else _setup(ids, c)
    if st is None:
        return None, {"reason": "no solid blocks"}
    air, sm, lo, hi, inbb, grid, doors, clim = st[:8]
    if geo is not None:
        off = np.zeros(3, int)
    else:
        dom = set(map(tuple, np.argwhere(inbb & ~sm)))
        if not dom:
            if c.access_min_nodes == 0:
                return 0.0, {"access_zero_annotated": "no interior cells (fully solid): access is 0 by convention"}
            return None, {"reason": "no interior cells (fully solid)"}
        off, _ = _align_off(air.shape, grid.shape,
                            np.asarray(ids).shape, xyz, dom)
    idx = xyz + off
    ok = ((idx >= 0).all(1) & (idx < np.array(air.shape)).all(1))
    idx = idx[ok]
    vn = omega_raw[ok] * (1.0 - c.gamma)

    vgrid = np.zeros(air.shape, float)
    hasv = np.zeros(air.shape, bool)
    vgrid[idx[:, 0], idx[:, 1], idx[:, 2]] = vn
    hasv[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    clim_eff = clim if c.climbable_enabled else np.zeros_like(clim)
    S = WK.nodes(air, sm, doors, clim_eff)
    uni = S & hasv
    n = int(uni.sum())
    inter = {"n_walk_nodes": n}
    if n < c.access_min_nodes:
        inter["reason"] = f"fewer than {c.access_min_nodes} walkable cells with a field value"
        return None, inter
    if c.access_min_nodes == 0 and n == 0:
        inter["access_zero_annotated"] = "no walkable cells: access is 0 by convention"
        return 0.0, inter
    vals = vgrid[uni]
    mtot = float(vals.sum())
    if mtot <= 0:
        if c.access_min_nodes == 0:
            inter["access_zero_annotated"] = "zero walkable omega mass: access is 0 by convention"
            return 0.0, inter
        inter["reason"] = "zero walkable omega mass"
        return None, inter
    lab, npieces = WK.pieces(uni, clim_eff)
    cs = np.argwhere(uni)
    per = {}
    for i2 in range(len(cs)):
        per.setdefault(int(lab[tuple(cs[i2])]), []).append(float(vals[i2]))
    trip = [(float(np.sum(v)), float(np.min(v)), float(np.max(v)))
            for v in per.values()]
    inter["n_walk_pieces"] = npieces
    inter["largest_piece_mass_frac"] = round(max(m for m, _, _ in trip) / mtot, 4)

    v_range = sum(m * (hi - lo) for m, lo, hi in trip) / mtot
    v_sq = sum(m * (hi * hi - lo * lo) for m, lo, hi in trip) / mtot
    inter["access_range"] = round(v_range, 4)
    inter["access_sq"] = round(v_sq, 4)

    if c.access_warp == "range":
        return round(v_range, 4), inter
    if c.access_warp == "sq":
        return round(v_sq, 4), inter
    raise ValueError(
        "access_warp must be 'range' (release default) or 'sq' (hi^2 - lo^2); got %r" % (c.access_warp,))


def field_for(ids, c=DEFAULTS):
    from . import field as FLD
    st = _setup(ids, c)
    if st is None:
        return None, None
    wall = st.wall
    d, w = FLD.quadrature(FLD.PAPER_SETTINGS["quadrature"])
    v, _meta = FLD.solve(wall, st.inbb, d, w, c.gamma)
    score = st.scoring_region
    off = (np.array(st.air.shape) - np.array(np.asarray(ids).shape)) // 2
    return np.argwhere(score) - off, v[score]


def field_from_geometry(geo, c=DEFAULTS):
    from . import field as FLD
    d, w = FLD.quadrature(FLD.PAPER_SETTINGS["quadrature"])
    v, _meta = FLD.solve(geo.wall, geo.inbb, d, w, c.gamma)
    score = geo.scoring_region
    return np.argwhere(score), v[score]


def measure_geometry(geo, c=DEFAULTS):
    xyz, om = field_from_geometry(geo, c)
    if not len(xyz):
        if c.access_min_nodes == 0:
            return Measures(shelter=0.0, access=0.0,
                            intermediates={"reason": "no interior cells",
                                           "shelter_zero_annotated": "no interior cells: both measures are 0 by convention",
                                           "access_zero_annotated": "no interior cells: both measures are 0 by convention"})
        return Measures(shelter=None, access=None,
                        intermediates={"reason": "no interior cells"})
    sh, i1 = shelter_from_field(None, xyz, om, c, geo=geo)
    ac, i2 = access_from_field(None, xyz, om, c, geo=geo)
    inter = {k: v for k, v in i1.items() if k != "reason"}
    inter.update({k: v for k, v in i2.items() if k != "reason"})
    for tag, src in (("shelter", i1), ("access", i2)):
        if "reason" in src and (sh if tag == "shelter" else ac) is None:
            inter[f"{tag}_none_reason"] = src["reason"]
    return Measures(shelter=sh, access=ac, intermediates=inter)


def measure(build, xyz=None, omega_raw=None, c=DEFAULTS):
    ids = build.ids if hasattr(build, "ids") else build
    if xyz is None or omega_raw is None:
        xyz, omega_raw = field_for(ids, c)
        if xyz is None:
            return Measures(shelter=None, access=None,
                            intermediates={"reason": "no solid blocks"})
    sh, i1 = shelter_from_field(ids, xyz, omega_raw, c)
    ac, i2 = access_from_field(ids, xyz, omega_raw, c)
    inter = {k: v for k, v in i1.items() if k != "reason"}
    inter.update({k: v for k, v in i2.items() if k != "reason"})
    for tag, src in (("shelter", i1), ("access", i2)):
        if "reason" in src and (sh if tag == "shelter" else ac) is None:
            inter[f"{tag}_none_reason"] = src["reason"]
    return Measures(shelter=sh, access=ac, intermediates=inter)
