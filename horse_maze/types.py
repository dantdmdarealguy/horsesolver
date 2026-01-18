from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set

Coord = Tuple[int, int]

@dataclass(frozen=True)
class Cell:
    token: str              # original token, like ".", "W", "P0", etc.
    kind: str               # "wall", "air", "horse", "item", "portal"
    value: int              # score value if enclosed (reachable with horse)
    portal_id: Optional[str] = None  # label for portals (e.g., "0", "a", "Z")

@dataclass
class Puzzle:
    rows: int
    cols: int
    max_blocks: int
    grid: List[List[Cell]]
    horse: Coord
    portals: Dict[str, List[Coord]]  # portal_id -> [coord1, coord2]

@dataclass
class Solution:
    feasible: bool
    max_score: int
    blocks: Set[Coord]              # where blocks are placed (on air only)
    reachable: Set[Coord]           # enclosed region (horse reachable)
