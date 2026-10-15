from __future__ import annotations

import json
import os.path as osp
import subprocess
import sys
import textwrap

HERE = osp.dirname(osp.abspath(__file__))
PKG = osp.dirname(HERE)
CODE = osp.dirname(PKG)
ROOT = osp.dirname(osp.dirname(CODE))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_locate", osp.join(HERE, "_locate.py"))
_loc = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_loc)
_REL = _loc.release_root(__file__)
if not _REL:
    raise SystemExit("this test needs a copy of the VoxHouse3D release (a directory containing "
                     "geometry/ and measures/measures.csv) above or beside the package; none found")

SAMPLE = osp.join(_REL, "geometry", "VH3D-w03-a78fe8df.npz")
EXPECT = (0.6526, 0.7641)

CHILD = '''
import sys, json
P = {root!r}
sys.path = [p for p in sys.path if not p.startswith(P) or ".venv" in p] + [{pkgroot!r}]
out = {{}}
try:
    import structgauge as sg
    out["import"] = True
    b = sg.load({sample!r})
    m = sg.measure(b)
    out["shelter"], out["access"] = m.shelter, m.access
except Exception as e:
    out["error"] = f"{{type(e).__name__}}: {{e}}"
print("@@" + json.dumps(out))
'''


def main() -> int:
    src = CHILD.format(root=ROOT, sample=SAMPLE, pkgroot=CODE)
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(src)],
                       capture_output=True, text=True, cwd="/", timeout=900)
    line = [x for x in r.stdout.splitlines() if x.startswith("@@")]
    if not line:
        print("  FAIL: the subprocess did not report: " + (r.stderr.strip()[-400:] or "(no stderr)"))
        return 1
    o = json.loads(line[0][2:])

    fails = []
    i1 = o.get("import") is True and "error" not in o
    print("  I1 imports in a clean process: " + ("ok" if i1 else "FAIL " + str(o.get("error"))))
    if not i1:
        fails.append("I1")
    got = (o.get("shelter"), o.get("access"))
    i2 = got == EXPECT
    print("  I2 readings match the released table: %s vs %s -> %s" % (got, EXPECT, "ok" if i2 else "FAIL"))
    if not i2:
        fails.append("I2")
    if fails:
        print("  FAILED: " + ", ".join(fails))
        return 1
    print("  all 2 checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
