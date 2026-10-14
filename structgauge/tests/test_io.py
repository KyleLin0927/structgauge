from __future__ import annotations
import glob
import os.path as osp
import sys
import tempfile

HERE = osp.dirname(osp.abspath(__file__))
sys.path.insert(0, osp.dirname(osp.dirname(HERE)))
import numpy as np
from structgauge.io import npz as IO

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_locate", osp.join(HERE, "_locate.py"))
_loc = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_loc)


def test_release_format():
    rel = _loc.release_root(__file__)
    files = sorted(glob.glob(osp.join(rel, "geometry", "*.npz"))) if rel else []
    if not files:
        print("  T1 release format: no copy of the VoxHouse3D release found -> FAIL (a skipped check does not count as a pass)")
        return False
    b = IO.load(files[0])
    print("  T1 release format (vocab + blockstates) loads: %s -> ok" % (b,))
    ok = True
    with tempfile.TemporaryDirectory() as td:
        bad = osp.join(td, "bad.npz")
        z = np.load(files[0])
        np.savez_compressed(bad, blockstates=z["blockstates"])
        try:
            IO.load(bad)
            print("  T2 a file without `vocab` must raise: FAIL (no exception)")
            ok = False
        except KeyError:
            print("  T2 a file without `vocab` must raise: ok")
    return ok


def main():
    fails = []
    rng = np.random.default_rng(20260817)
    ids = rng.integers(0, 4, size=(5, 6, 7)).astype(np.int16)

    try:
        IO.from_array(np.zeros((3, 3)))
        fails.append("I1: a 2-D array was accepted")
        print("  I1 a 2-D array is rejected: FAIL")
    except ValueError:
        print("  I1 a 2-D array is rejected: ok")

    with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
        np.savez(f.name, ids=ids)
        b = IO.load(f.name)
    ok2 = b.data.shape == ids.shape and int(b.data.sum()) == 0
    if not ok2:
        fails.append("I2: missing `data` was not zero-filled (%r)" % (b.data.shape,))
    print("  I2 a missing `data` field is zero-filled: %s" % ("ok" if ok2 else "FAIL"))

    ok3 = b.dims == ids.shape and b.n_solid == int((ids > 0).sum())
    if not ok3:
        fails.append("I3: dims or n_solid do not match the array")
    print("  I3 dims and n_solid match the array: %s" % ("ok" if ok3 else "FAIL"))

    if not test_release_format():
        fails.append("release format")
    if fails:
        print("\n  FAILED (%d): %s" % (len(fails), fails))
        return 1
    print("\n  all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
