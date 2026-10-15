from __future__ import annotations

AIR = 0

NON_SOLID_BLOCK_IDS = frozenset({
    6, 8, 9, 10, 11, 27, 28, 30, 31, 32, 36, 37,
    38, 39, 40, 50, 51, 55, 59, 63, 65, 66, 68, 69,
    70, 72, 75, 76, 77, 78, 83, 90, 93, 94, 104, 105,
    106, 111, 115, 119, 131, 132, 141, 142, 143, 144, 147, 148,
    149, 150, 157, 171, 175, 176, 177, 207, 209, 217, 253, 254,
})

DOOR_BLOCK_IDS = frozenset({
    64, 71, 96, 107, 167, 183, 184, 185, 186, 187, 193, 194,
    195, 196, 197,
})

CLIMBABLE_BLOCK_IDS = frozenset({
    65, 106,
})

GAME_VERSION = "Minecraft 1.12 (pre-flattening numeric block ids 0-255)"
TABLE_SOURCE = "classification derived from the official collision-shape dump; no game files are included"
TABLE_COUNTS = {"non_solid": len(NON_SOLID_BLOCK_IDS), "door": len(DOOR_BLOCK_IDS), "climbable": len(CLIMBABLE_BLOCK_IDS)}
KNOWN_DEVIATIONS = (
    "slabs: the voxel model cannot represent upper/lower halves; a slab occupies its whole cell",
    "carpets, pressure plates, lily pads and snow layers (height <= 0.25): treated as non-solid, so they neither block movement nor count as standable surfaces",
    "ladders (65) and vines (106): the official collision box is solid; treated as non-solid so that climbing connects floors",
    "the 15 door, trapdoor and fence-gate blocks: solid when closed in the game; always treated as non-solid, so an entrance is a passage and not a wall gap",
)
