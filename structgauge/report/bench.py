from __future__ import annotations

import json
import os
import os.path as osp
import random

_REF = osp.join(osp.dirname(osp.abspath(__file__)), "bench_reference.json")


def reference():
    with open(_REF, encoding="utf-8") as f:
        return json.load(f)


def _ci(flags, B=2000, seed=20260831):
    n = len(flags)
    if n == 0:
        return None
    rnd = random.Random(seed)
    vals = sorted(sum(flags[rnd.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return [round(vals[int(0.025 * B)], 4), round(vals[int(0.975 * B) - 1], 4)]


def bench_rows(readings, thr_s, thr_a, B=2000, seed=20260831):
    sh = [1 if s < thr_s else 0 for _, s, _ in readings]
    ac = [1 if a < thr_a else 0 for _, _, a in readings]
    ei = [1 if (s < thr_s or a < thr_a) else 0 for _, s, a in readings]
    n = len(readings)
    out = {"n": n,
           "shelter_alarm": round(sum(sh) / n, 4), "shelter_ci95": _ci(sh, B, seed),
           "access_alarm": round(sum(ac) / n, 4), "access_ci95": _ci(ac, B, seed),
           "either": round(sum(ei) / n, 4), "either_ci95": _ci(ei, B, seed)}
    return out


def bench_folder(folder, thr_s=None, thr_a=None, B=2000, seed=20260831, label=None):
    from .. import load, measure, __version__
    files = sorted(f for f in os.listdir(folder) if f.endswith(".npz"))
    if not files:
        raise SystemExit("ERROR: no .npz files in folder: %s" % folder)
    per = []
    n_unmeasurable = 0
    for f in files:
        r = measure(load(osp.join(folder, f)))
        if r.shelter is None or r.access is None:
            n_unmeasurable += 1
            continue
        per.append((f, float(r.shelter), float(r.access)))
    if not per:
        raise SystemExit("ERROR: none of the %d files could be measured (no solid blocks)" % n_unmeasurable)
    ref = reference()
    fs, fa = ref["_frozen"]["threshold_shelter"], ref["_frozen"]["threshold_access"]
    if thr_s is None: thr_s = fs
    if thr_a is None: thr_a = fa
    if abs(thr_s - fs) > 1e-12 or abs(thr_a - fa) > 1e-12:
        note = "WARNING: thresholds (%.5g, %.5g) differ from the frozen 10th-percentile thresholds (%.5g, %.5g); reference rows are not comparable, sensitivity check only" % (thr_s, thr_a, fs, fa)
    else:
        note = None
    res = {"label": label or osp.basename(osp.abspath(folder)),
           "threshold_shelter": thr_s, "threshold_access": thr_a, "B": B, "seed": seed,
           "yours": bench_rows(per, thr_s, thr_a, B, seed),
           "reference_rows": ref["rows"], "frozen": ref["_frozen"],
           "structgauge_version": __version__, "n_unmeasurable": n_unmeasurable,
           "semantics": ref["_semantics"], "threshold_mismatch": note}
    return res, per


def _table(header, rows, align_right=None):
    align_right = align_right or set()
    cols = len(header)
    w = [max(len(str(r[k])) for r in [header] + rows) for k in range(cols)]
    def line(l, m, r):
        return l + m.join("─" * (w[k] + 2) for k in range(cols)) + r
    def row(r):
        cells = []
        for k in range(cols):
            v = str(r[k])
            cells.append((" " + v.rjust(w[k]) + " ") if k in align_right else (" " + v.ljust(w[k]) + " "))
        return "│" + "│".join(cells) + "│"
    out = [line("┌", "┬", "┐"), row(header), line("├", "┼", "┤")]
    out += [row(r) for r in rows]
    out.append(line("└", "┴", "┘"))
    return out


def _ci_fmt(ci):
    return "[-, -]" if ci is None else "[%.4f, %.4f]" % (ci[0], ci[1])


def render(res):
    L = []
    L.append("structgauge bench | one-sided alarm rates (%s thresholds: shelter %.4f / access %.4f; a rate is the share of builds below the threshold, not a severity)"
             % ("CUSTOM" if res["threshold_mismatch"] else "frozen human-house 10th-percentile", res["threshold_shelter"], res["threshold_access"]))
    y = res["yours"]
    rows = [["* " + res["label"], y["n"],
             "%.4f %s" % (y["shelter_alarm"], _ci_fmt(y["shelter_ci95"])),
             "%.4f %s" % (y["access_alarm"], _ci_fmt(y["access_ci95"])),
             "%.4f %s" % (y["either"], _ci_fmt(y["either_ci95"]))]]
    for name, r in res["reference_rows"].items():
        rows.append([name, r["n"], "%.4f" % r["shelter_alarm"], "%.4f" % r["access_alarm"], "%.4f" % r["either"]])
    L += _table(["source", "n", "shelter alarm [95% CI]", "access alarm [95% CI]", "either [95% CI]"], rows, align_right={1})
    if res["threshold_mismatch"]:
        L.append(res["threshold_mismatch"])
    if res["n_unmeasurable"]:
        L.append("note: %d of %d files had no solid blocks and could not be measured; they are not counted in n"
                 % (res["n_unmeasurable"], res["n_unmeasurable"] + res["yours"]["n"]))
    f = res["frozen"]
    L.append("frozen: line=(%.5g, %.5g) = human-house 10th percentile; gamma=%s; block semantics=%s; reference=%s"
             % (f["threshold_shelter"], f["threshold_access"], f["gamma"], f["block_semantics"], f["reference_dataset"]))
    return "\n".join(L)
