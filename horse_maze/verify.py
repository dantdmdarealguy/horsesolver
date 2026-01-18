from __future__ import annotations
from collections import deque
from typing import Set, Dict, List, Tuple

from horse_maze.types import Puzzle, Solution, Coord
from horse_maze.grid import is_boundary, neighbors_4

def compute_reachable(p: Puzzle, blocks: Set[Coord]) -> Set[Coord]:
    """
    True reachability from the horse, respecting:
      - Walls are impassable
      - Blocks (placed only on air) are impassable
      - Portals teleport between their pair (bidirectional)
    """
    start = p.horse
    q = deque([start])
    seen: Set[Coord] = {start}

    # build portal mapping coord -> paired coord
    portal_pair: Dict[Coord, Coord] = {}
    for pid, coords in p.portals.items():
        a, b = coords
        portal_pair[a] = b
        portal_pair[b] = a

    def passable(rc: Coord) -> bool:
        r, c = rc
        cell = p.grid[r][c]
        if cell.kind == "wall":
            return False
        if rc in blocks:
            return False
        return True

    while q:
        u = q.popleft()

        # normal moves
        for v in neighbors_4(p, u):
            if passable(v) and v not in seen:
                seen.add(v)
                q.append(v)

        # portal teleport
        r, c = u
        if p.grid[r][c].kind == "portal":
            v = portal_pair.get(u)
            if v is not None and passable(v) and v not in seen:
                seen.add(v)
                q.append(v)

    return seen

def score_region(p: Puzzle, region: Set[Coord]) -> int:
    s = 0
    for (r, c) in region:
        s += p.grid[r][c].value
    return s

def verify_solution(p: Puzzle, sol: Solution) -> str:
    """
    Returns a human-readable report verifying:
    - blocks only on air
    - horse cannot reach boundary
    - computed score matches solver-reported score
    """
    # blocks validity
    for (r, c) in sol.blocks:
        cell = p.grid[r][c]
        if cell.kind != "air":
            return f"INVALID: block placed on non-air at ({r},{c}) token={cell.token}"

    region = compute_reachable(p, sol.blocks)

    # boundary escape check
    escapes = [rc for rc in region if is_boundary(p, rc)]
    if escapes:
        # show a few
        sample = ", ".join(str(x) for x in escapes[:8])
        return f"INVALID: horse can reach boundary cell(s): {sample}"

    computed_score = score_region(p, region)
    if computed_score != sol.max_score:
        return f"INVALID: score mismatch. solver={sol.max_score}, computed={computed_score}"

    # Also check solver's stored reachable set (if you keep it)
    if sol.reachable and sol.reachable != region:
        return f"WARNING: solver.reachable differs from computed reachability (but enclosure/score may still be ok)."

    return "OK: solution is valid (enclosed) and score matches simulation."
