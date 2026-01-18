from __future__ import annotations
from typing import Dict, List, Tuple, Iterable, Set
from horse_maze.types import Puzzle, Coord

def in_bounds(p: Puzzle, r: int, c: int) -> bool:
    return 0 <= r < p.rows and 0 <= c < p.cols

def is_boundary(p: Puzzle, rc: Coord) -> bool:
    r, c = rc
    return r == 0 or r == p.rows - 1 or c == 0 or c == p.cols - 1

def neighbors_4(p: Puzzle, rc: Coord) -> List[Coord]:
    r, c = rc
    cand = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    return [(rr, cc) for rr, cc in cand if in_bounds(p, rr, cc)]

def build_adjacency(p: Puzzle) -> Dict[Coord, List[Coord]]:
    """
    Adjacency among all non-wall cells, including portal teleport edges.
    (Blocks are handled later by the solver as "removed air cells".)
    """
    adj: Dict[Coord, List[Coord]] = {}

    # Add normal grid adjacency for non-walls
    for r in range(p.rows):
        for c in range(p.cols):
            if p.grid[r][c].kind == "wall":
                continue
            rc = (r, c)
            adj.setdefault(rc, [])
            for nb in neighbors_4(p, rc):
                rr, cc = nb
                if p.grid[rr][cc].kind != "wall":
                    adj[rc].append(nb)

    # Add portal edges
    for pid, coords in p.portals.items():
        a, b = coords
        # Both cells are non-wall by construction
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    return adj
