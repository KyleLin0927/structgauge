from __future__ import annotations

import numpy as np

PAPER_SETTINGS = {
    "quadrature": 4,
    "gamma": 0.9,
    "supercover": True,
}

_EPS = 1e-12


def quadrature(order: int = 4):
    if order == 4:
        m1 = 1.0 / 3.0 - np.sqrt(10.0) / 15.0
        mus = np.sqrt([m1, 1.0 - 2.0 * m1])
        shapes = {(0, 0, 1): 1.0 / 24.0}
    elif order == 6:
        m1 = 0.23009194 ** 2
        cc = (1.0 - 3.0 * m1) / 2.0
        mus = np.sqrt([m1, m1 + cc, m1 + 2 * cc])
        den = 120.0 * (9 * m1 ** 2 - 6 * m1 + 1)
        shapes = {(0, 0, 2): (-15 * m1 ** 2 + 10 * m1 + 1) / den,
                  (0, 1, 1): (15 * m1 ** 2 - 10 * m1 + 1) / (den / 4)}
    else:
        raise ValueError(
            f"only S4 and S6 quadrature sets are implemented; got S{order}. "
            "Wrong quadrature constants do not raise, they silently bias the field.")

    from itertools import permutations
    dirs, wts, seen = [], [], set()
    for shape, w in shapes.items():
        for perm in set(permutations([mus[i] for i in shape])):
            for sx in (1, -1):
                for sy in (1, -1):
                    for sz in (1, -1):
                        v = (sx * perm[0], sy * perm[1], sz * perm[2])
                        key = tuple(round(t, 12) for t in v)
                        if key in seen:
                            continue
                        seen.add(key)
                        dirs.append(v)
                        wts.append(w)
    d = np.array(dirs, float)
    w = np.array(wts, float)
    n_expect = order * (order + 2)
    if len(d) != n_expect:
        raise AssertionError(f"S{order} should have {n_expect} directions; got {len(d)}")
    return d / np.linalg.norm(d, axis=1, keepdims=True), w / w.sum()


def first_hit(solid, capture, dirs, supercover: bool = PAPER_SETTINGS["supercover"]):
    solid = np.asarray(solid, bool)
    capture = np.asarray(capture, bool)
    shp = np.array(solid.shape)
    n = int(np.prod(shp))
    flat = np.arange(n, dtype=np.int64).reshape(shp)
    gi_, gj_, gk_ = (a.ravel().astype(np.int64) for a in np.indices(shp))
    max_steps = int(shp.sum()) * 3 + 8

    nxt_all, state_all = [], []
    for d in np.asarray(dirs, float):
        d = d / np.linalg.norm(d)
        cx, cy, cz = gi_.copy(), gj_.copy(), gk_.copy()
        step = np.sign(d).astype(np.int64)
        tdelta = np.where(np.abs(d) > _EPS,
                          1.0 / np.maximum(np.abs(d), _EPS), np.inf)
        tmax = np.empty((3, n), float)
        for ax, (c0, p0) in enumerate(((cx, gi_ + 0.5), (cy, gj_ + 0.5),
                                       (cz, gk_ + 0.5))):
            if abs(d[ax]) <= _EPS:
                tmax[ax] = np.inf
            else:
                tmax[ax] = (c0 + (1 if d[ax] > 0 else 0) - p0) / d[ax]

        alive = np.ones(n, bool)
        state = np.zeros(n, np.int8)
        nxt = np.full(n, -1, np.int64)
        for _ in range(max_steps):
            if not alive.any():
                break
            a = np.flatnonzero(alive)
            tm = tmax[:, a]
            adv = tm <= tm.min(axis=0) + _EPS

            if supercover:
                a, adv = _supercover_block(solid, shp, flat, step, a, adv,
                                           cx, cy, cz, nxt, state, alive)
                if a.size == 0:
                    continue

            for ax, cur in enumerate((cx, cy, cz)):
                m = adv[ax]
                cur[a[m]] += step[ax]
                tmax[ax, a[m]] += tdelta[ax]
            ni, nj, nk = cx[a], cy[a], cz[a]
            oob = ((ni < 0) | (ni >= shp[0]) | (nj < 0) | (nj >= shp[1])
                   | (nk < 0) | (nk >= shp[2]))
            ic, jc, kc = (np.clip(ni, 0, shp[0] - 1), np.clip(nj, 0, shp[1] - 1),
                          np.clip(nk, 0, shp[2] - 1))
            hit = solid[ic, jc, kc] & ~oob
            esc = (oob | ~capture[ic, jc, kc]) & ~hit

            gh = a[hit]
            if gh.size:
                keep = (cx[gh].copy(), cy[gh].copy(), cz[gh].copy())
                for ax, cur in enumerate((cx, cy, cz)):
                    cur[gh[adv[ax][hit]]] -= step[ax]
                nxt[gh] = flat[cx[gh], cy[gh], cz[gh]]
                state[gh] = 1
                alive[gh] = False
                cx[gh], cy[gh], cz[gh] = keep
            ge = a[esc]
            if ge.size:
                state[ge] = 0
                alive[ge] = False
        nxt_all.append(nxt)
        state_all.append(state)
    return np.stack(nxt_all), np.stack(state_all)


def _supercover_block(solid, shp, flat, step, a, adv, cx, cy, cz,
                      nxt, state, alive):
    smask = (adv[0].astype(np.int8) | (adv[1].astype(np.int8) << 1)
             | (adv[2].astype(np.int8) << 2))
    blocked = np.zeros(len(a), bool)
    base = (cx[a], cy[a], cz[a])
    for sub in range(1, 7):
        sel = ((smask & sub) == sub) & (smask != sub)
        if not sel.any():
            continue
        g = np.flatnonzero(sel)
        si, sj, sk = base[0][g].copy(), base[1][g].copy(), base[2][g].copy()
        if sub & 1:
            si += step[0]
        if sub & 2:
            sj += step[1]
        if sub & 4:
            sk += step[2]
        ob = ((si < 0) | (si >= shp[0]) | (sj < 0) | (sj >= shp[1])
              | (sk < 0) | (sk >= shp[2]))
        blocked[g] |= solid[np.clip(si, 0, shp[0] - 1),
                            np.clip(sj, 0, shp[1] - 1),
                            np.clip(sk, 0, shp[2] - 1)] & ~ob
    if blocked.any():
        bi = a[blocked]
        nxt[bi] = flat[cx[bi], cy[bi], cz[bi]]
        state[bi] = 1
        alive[bi] = False
        return a[~blocked], adv[:, ~blocked]
    return a, adv


def solve(solid, capture, dirs, weights, gamma: float, hitmaps=None):
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl

    nd = len(dirs)
    w = np.asarray(weights, float)
    if len(w) != nd:
        raise ValueError(f"number of weights ({len(w)}) != number of directions ({nd})")
    nxt, st = (first_hit(solid, capture, dirs) if hitmaps is None else hitmaps)

    dom = (np.asarray(capture, bool) & ~np.asarray(solid, bool)).ravel()
    ids = np.flatnonzero(dom)
    pos = -np.ones(dom.size, np.int64)
    pos[ids] = np.arange(len(ids))
    if len(ids) == 0:
        return np.zeros(np.asarray(solid).shape, float), {
            "n_unknown": 0, "nnz": 0, "gmres_info": 0, "resid_inf": 0.0,
            "error_bound": 0.0, "note": "no interior cells (fully solid)"}
    h = (st[:, ids] * w[:, None]).sum(axis=0)

    rows, cols, vals = [], [], []
    for k in range(nd):
        src = np.flatnonzero(st[k, ids] == 1)
        dst = pos[nxt[k, ids][st[k, ids] == 1]]
        ok = dst >= 0
        rows.append(src[ok])
        cols.append(dst[ok])
        vals.append(np.full(int(ok.sum()), w[k]))
    kmat = sp.coo_matrix((np.concatenate(vals),
                          (np.concatenate(rows), np.concatenate(cols))),
                         shape=(len(ids), len(ids))).tocsr()
    amat = sp.identity(len(ids), format="csr") - gamma * kmat

    v, info = spl.gmres(amat, h, rtol=1e-14, maxiter=5000)
    r_inf = float(np.abs(amat @ v - h).max())
    one = np.ones(len(ids))
    x1, _ = spl.gmres(amat, one, rtol=1e-14, maxiter=5000)
    r1 = float(np.abs(amat @ x1 - one).max())
    ainv = (float(np.abs(x1).max())
            if r1 <= 1e-8 * max(1.0, float(np.abs(x1).max())) else float("inf"))
    bound = r_inf * ainv
    scale = float(np.abs(v).max()) or 1.0
    if not ((bound <= 1e-9) or (bound / scale <= 1e-12)):
        raise RuntimeError(
            f"field solve did not converge to usable precision: ||r||_inf={r_inf:.3e}, "
            f"error bound {bound:.3e} (relative {bound/scale:.3e}), ||A^-1||_inf={ainv:.3e}, "
            f"n={len(ids)}, gamma={gamma}. If ||A^-1||_inf is of order 1e15 the system has no "
            "finite solution.")
    out = np.zeros(np.asarray(solid).shape).ravel()
    out[ids] = v
    return out.reshape(np.asarray(solid).shape), {
        "n_unknown": int(len(ids)), "nnz": int(kmat.nnz),
        "gmres_info": int(info), "resid_inf": r_inf, "error_bound": bound}


def omega(solid, capture, gamma: float = PAPER_SETTINGS["gamma"],
          order: int = PAPER_SETTINGS["quadrature"]):
    d, w = quadrature(order)
    v, meta = solve(solid, capture, d, w, gamma)
    return (1.0 - gamma) * v, {**meta, "gamma": gamma, "n_dir": len(d)}
