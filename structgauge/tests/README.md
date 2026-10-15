# Tests shipped with `structgauge`

Both tests need a copy of the VoxHouse3D release (they look upward for a directory containing `geometry/` and `measures/measures.csv`, or, failing that, for the newest release under `data/release/`), and nothing else.

| test | what it checks |
|---|---|
| `test_standalone.py` | in a subprocess with every project path stripped, the package imports, measures a known build, and returns the published readings |
| `test_io.py` | the two-column release format loads; a 2-D array is rejected; a missing `data` field is zero-filled; `dims` equals the array shape |

```
python structgauge/tests/test_standalone.py
python structgauge/tests/test_io.py
```

Regression tests against the authors' unpublished original implementation are not included.
