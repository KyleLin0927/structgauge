from __future__ import annotations

import glob
import os.path as osp
import re


def _is_release(d):
    return osp.isdir(osp.join(d, "geometry")) and osp.exists(osp.join(d, "measures", "measures.csv"))


def release_root(start=None):
    d = osp.dirname(osp.abspath(start or __file__))
    for _ in range(8):
        if _is_release(d):
            return d
        nd = osp.dirname(d)
        if nd == d:
            break
        d = nd
    d = osp.dirname(osp.abspath(start or __file__))
    for _ in range(8):
        rel = osp.join(d, "data", "release")
        if osp.isdir(rel):
            cands = [p for p in glob.glob(osp.join(rel, "*")) if _is_release(p)]
            if cands:
                def _key(p):
                    m = re.search(r"v(\d+)\.(\d+)", osp.basename(p))
                    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
                return sorted(cands, key=_key)[-1]
        nd = osp.dirname(d)
        if nd == d:
            break
        d = nd
    return None
