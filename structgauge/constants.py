from __future__ import annotations
import os
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

    quantile_eps: float = 1e-9

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
    "block_table_generator_version": "12.0.0",
    "mc_assets_version": "26.2",
    "legacy_id_space": "1.12 (pre-flattening numeric block ids 0-255)",
    "block_semantics": "v2 (official collision boxes)",
    "note": ("Rendering uses the 26.2 asset set; the structural measures use 1.12 block semantics. "
             "Both are pinned deliberately and must not be mixed within one judgement."),
}

DEFAULTS = Constants()

ENV_MAP = {
    "MCSE_BLOCK_SEM": ("block_semantics", str),
    "MCSE_Q1_REGION": ("scoring_region", str),
    "MCSE_ACC_WARP": ("access_warp", str),
    "MCSE_ACC_MIN_NODES": ("access_min_nodes", int),
    "MCSE_A152_DOORS": ("doors_in_scoring_region", lambda v: v != "0"),
    "MCSE_D7_CLIM": ("climbable_enabled", lambda v: v != "0"),
    "MCSE_LNQ_QEPS": ("quantile_eps", float),
}


def from_env(strict=True):
    kw, seen = {}, []
    for env, (field, cast) in ENV_MAP.items():
        v = os.environ.get(env)
        if v is not None:
            kw[field] = cast(v)
            seen.append("%s=%s" % (env, v))
    if seen and strict:
        print("structgauge: legacy environment variables detected: %s\n"
              "   They were read into explicit parameters; prefer passing Constants(...) directly."
              % ", ".join(seen))
    return Constants(**kw), seen


if __name__ == "__main__":
    print("structgauge constants (release defaults):")
    print(DEFAULTS.describe())
    c, seen = from_env()
    print("\nfields overridden from the environment: %s" % (seen or "(none)"))
