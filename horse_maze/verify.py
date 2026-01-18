from __future__ import annotations
from collections import deque
from typing import Set, Dict, List, Optional, Tuple

from horse_maze.types import Puzzle, Solution, Coord
from horse_maze.grid import is_boundary, neighbors_4

def _build_portal_pair(p: Puzzle) -> Dict[Coord, Coord]:
    portal_pair: Dict[Coord, Coord] = {}
    for pid, coords in p.portals.items():
        a, b = coords
        portal_pair[a] = b
        portal_pair[b] = a
    return portal_pair

def compute_reachable(p: Puzzle, blocks: Set[Coord]) -> Set[Coord]:
    start = p.horse
    q = deque([start])
    seen: Set[Coord] = {start}

    portal_pair = _build_portal_pair(p)

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

        for v in neighbors_4(p, u):
            if passable(v) and v not in seen:
                seen.add(v)
                q.append(v)

        ur, uc = u
        if p.grid[ur][uc].kind == "portal":
            v = portal_pair.get(u)
            if v is not None and passable(v) and v not in seen:
                seen.add(v)
                q.append(v)

    return seen

def score_region(p: Puzzle, region: Set[Coord]) -> int:
    return sum(p.grid[r][c].value for (r, c) in region)

def find_escape_path(p: Puzzle, blocks: Set[Coord]) -> Optional[List[Coord]]:
    """
    If the horse can reach any boundary non-wall cell, return ONE shortest path
    (including portal jumps) as a list of coords from horse -> boundary.
    Otherwise return None.
    """
    start = p.horse
    portal_pair = _build_portal_pair(p)

    def passable(rc: Coord) -> bool:
        r, c = rc
        cell = p.grid[r][c]
        if cell.kind == "wall":
            return False
        if rc in blocks:
            return False
        return True

    q = deque([start])
    prev: Dict[Coord, Optional[Coord]] = {start: None}

    while q:
        u = q.popleft()

        # If u is boundary and passable and not a wall: escape found.
        if is_boundary(p, u) and passable(u):
            # reconstruct path
            path: List[Coord] = []
            cur: Optional[Coord] = u
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            return path

        # neighbors
        for v in neighbors_4(p, u):
            if passable(v) and v not in prev:
                prev[v] = u
                q.append(v)

        # portal
        ur, uc = u
        if p.grid[ur][uc].kind == "portal":
            v = portal_pair.get(u)
            if v is not None and passable(v) and v not in prev:
                prev[v] = u
                q.append(v)

    return None

def verify_solution(p: Puzzle, sol: Solution) -> str:
    # blocks validity
    for (r, c) in sol.blocks:
        cell = p.grid[r][c]
        if cell.kind != "air":
            return f"INVALID: block placed on non-air at ({r},{c}) token={cell.token}"

    region = compute_reachable(p, sol.blocks)

    # boundary escape check
    escapes = [rc for rc in region if is_boundary(p, rc)]
    if escapes:
        path = find_escape_path(p, sol.blocks)
        if path:
            return f"INVALID: horse can escape; example path: {path}"
        return f"INVALID: horse can reach boundary cell(s)."

    computed_score = score_region(p, region)
    if computed_score != sol.max_score:
        return f"INVALID: score mismatch. solver={sol.max_score}, computed={computed_score}"

    if sol.reachable and sol.reachable != region:
        return "WARNING: solver.reachable differs from computed reachability (enclosure/score still ok)."

    return "OK: solution is valid (enclosed) and score matches simulation."
