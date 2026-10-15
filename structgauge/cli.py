"""structgauge: shelter and access, two one-sided interior measures for voxel buildings."""
from __future__ import annotations

import argparse
import json
import sys


def _fmt(x):
    return "—" if x is None else f"{x:.4f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="structgauge", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("measure", help="print shelter and access for each file (columns: shelter, access, path)")
    m.add_argument("paths", nargs="+")
    m.add_argument("--json", action="store_true", help="machine-readable output")


    sub.add_parser("constants", help="print the effective constants")

    b = sub.add_parser("bench", help="one-sided alarm rates of a folder of builds next to the frozen reference rows (a rate is the share of builds below the threshold, not a severity; never rank single builds)")
    b.add_argument("folder")
    b.add_argument("--thr-shelter", type=float, default=None, help="override the frozen shelter threshold (default: 10th percentile of human houses)")
    b.add_argument("--thr-access", type=float, default=None, help="override the frozen access threshold (default: 10th percentile of human houses)")
    b.add_argument("--B", type=int, default=2000, help="bootstrap resamples for the 95%% CI (default 2000)")
    b.add_argument("--label", help="name of your row in the table (default: folder name)")
    b.add_argument("--json", action="store_true", help="print the result as JSON instead of a table")

    a = ap.parse_args(argv)

    if a.cmd == "bench":
        from .report.bench import bench_folder, render
        res, _per = bench_folder(a.folder, thr_s=a.thr_shelter, thr_a=a.thr_access, B=a.B, label=a.label)
        if a.json:
            json.dump(res, sys.stdout, ensure_ascii=False, indent=2); print()
        else:
            print(render(res))
        return 0

    from . import DEFAULTS, load, measure

    if a.cmd == "constants":
        from .report.bench import reference
        from .blocks import tables as _t
        out = dict(DEFAULTS.as_dict())
        fz = reference()["_frozen"]
        out["bench_threshold_shelter"] = fz["threshold_shelter"]
        out["bench_threshold_access"] = fz["threshold_access"]
        out["block_tables"] = {"game_version": _t.GAME_VERSION, "counts": _t.TABLE_COUNTS}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    rows = []
    for p in a.paths:
        b = load(p)
        res = measure(b)
        rows.append({"path": p, "shelter": res.shelter, "access": res.access})
        if getattr(a, "json", False):
            continue
        print(f"{_fmt(res.shelter)}  {_fmt(res.access)}  {p}")

    if a.cmd == "measure" and getattr(a, "json", False):
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
