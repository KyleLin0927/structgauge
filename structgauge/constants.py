from __future__ import annotations
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Constants:

    block_semantics: str = "v2"

    scoring_region: str = "full_bbox"

    doors_in_scoring_region: bool = True

    access_min_nodes: int = 0

    access_warp: str = "range"

    virtual_terrain: bool = False

    climbable_enabled: bool = True

    gamma: float = 0.9

    _SUPPORTED_SEMANTICS = ("v2",)

    def __post_init__(self):
        if not (0.0 <= self.gamma < 1.0):
            raise ValueError(
                "gamma must lie in [0, 1); got %r. For gamma >= 1 the system (I - gamma*K) is no "
                "longer a strictly diagonally dominant M-matrix and Omega loses its [0, 1] guarantee; "
                "for gamma < 0 the solve still returns finite values, so it would not fail, it would "
                "silently return wrong numbers." % (self.gamma,))
        if self.access_min_nodes < 0:
            raise ValueError("access_min_nodes must be >= 0 (0 = no cut-off, the release default)")
        if self.access_warp not in ("range", "sq"):
            raise ValueError(
                "access_warp=%r is not supported (only 'range' = hi - lo, the release default, "
                "or 'sq' = hi^2 - lo^2). This raises on purpose instead of falling back to 'range': "
                "a silent fallback would make a comparison between the two settings meaningless."
                % (self.access_warp,))
        if self.block_semantics not in self._SUPPORTED_SEMANTICS:
            raise NotImplementedError(
                "block_semantics=%r is not available in this package (supported: %s). "
                "This raises on purpose instead of falling back: a silent fallback would make a "
                "comparison between block-semantics versions meaningless."
                % (self.block_semantics, ", ".join(self._SUPPORTED_SEMANTICS)))

    def as_dict(self):
        return asdict(self)

    def describe(self, provenance=True):
        w = max(len(k) for k in self.as_dict())
        out = "\n".join("  %-*s = %r" % (w, k, v) for k, v in self.as_dict().items())
        if provenance:
            out += "\n\n  game-mechanics provenance (not tunable; where these tables come from):\n"
            pw = max(len(k) for k in PROVENANCE)
            out += "\n".join("    %-*s = %s" % (pw, k, v)
                             for k, v in PROVENANCE.items())
        return out


PROVENANCE = {
    "block_table_source": "official (unobfuscated) Minecraft jar dump of collision shapes",
    "mc_assets_version": "26.2",
    "legacy_id_space": "1.12 (pre-flattening numeric block ids 0-255)",
    "block_semantics": "v2 (official collision boxes)",
    "note": ("1.12 numeric block ids are mapped to the collision shapes of the Minecraft 26.2 jar; "
             "the table is pinned and is not a tunable parameter."),
}

DEFAULTS = Constants()

if __name__ == "__main__":
    print("structgauge constants (release defaults):")
    print(DEFAULTS.describe())
