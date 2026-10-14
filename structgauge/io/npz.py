from __future__ import annotations
import os.path as osp
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Build:
    ids: np.ndarray
    data: np.ndarray
    name: str = ""

    @property
    def dims(self):
        return tuple(self.ids.shape)

    @property
    def n_solid(self):
        return int((self.ids > 0).sum())

    def __repr__(self):
        return "Build(%s, dims=%s, solid=%d)" % (self.name or "?", self.dims,
                                                 self.n_solid)


_BUNDLED_MAP = osp.join(osp.dirname(osp.abspath(__file__)), "legacy_map.json")


def _legacy_map(path):
    import json
    d = osp.dirname(osp.abspath(path))
    for _ in range(3):
        cand = osp.join(d, "reproduce", "legacy_map.json")
        if osp.exists(cand):
            with open(cand, encoding="utf-8") as f:
                return json.load(f)
        d = osp.dirname(d)
    with open(_BUNDLED_MAP, encoding="utf-8") as f:
        return json.load(f)


def _legacy_pair(v):
    parts = v.split(":")
    if len(parts) in (2, 3) and parts[0] == "legacy":
        try:
            return int(parts[1]), (int(parts[2]) if len(parts) == 3 else 0)
        except ValueError:
            pass
    raise ValueError("block state %r is not in the legacy map and is not of the form "
                     "legacy:<id>[:<data>]; refusing to map it silently" % (v,))


def load(path):
    with np.load(path) as z:
        if "ids" in z:
            ids = np.asarray(z["ids"]).astype(np.int16)
            data = (np.asarray(z["data"]).astype(np.int16) if "data" in z
                    else np.zeros_like(ids))
        elif "blockstates" in z and "vocab" in z:
            vocab = [str(v) for v in np.asarray(z["vocab"]).tolist()]
            bs = np.asarray(z["blockstates"])
            lut_i = np.zeros(len(vocab), np.int16)
            lut_d = np.zeros(len(vocab), np.int16)
            m = _legacy_map(path)
            unknown = []
            for i, v in enumerate(vocab):
                if not v:
                    continue
                if v in m:
                    a, b = m[v]
                else:
                    try:
                        a, b = _legacy_pair(v)
                    except ValueError:
                        unknown.append(v)
                        continue
                lut_i[i], lut_d[i] = a, b
            if unknown:
                raise ValueError("%s: %d block state(s) cannot be mapped to the 1.12 id space "
                                 "(first: %s); refusing to treat them as air"
                                 % (path, len(unknown), unknown[:5]))
            ids, data = lut_i[bs], lut_d[bs]
        else:
            raise KeyError("npz has neither `ids` nor `vocab`/`blockstates`: "
                           "%s (fields: %s)" % (path, list(z.files)))
    if ids.ndim != 3:
        raise ValueError("ids must be 3-D; got shape %r" % (ids.shape,))
    return Build(ids=ids, data=data, name=osp.basename(path)[:-4])


def from_array(ids, data=None, name=""):
    ids = np.asarray(ids).astype(np.int16)
    if ids.ndim != 3:
        raise ValueError("ids must be 3-D; got shape %r" % (ids.shape,))
    return Build(ids=ids,
                 data=(np.zeros_like(ids) if data is None
                       else np.asarray(data).astype(np.int16)),
                 name=name)
