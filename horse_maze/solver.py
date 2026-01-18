from __future__ import annotations
from typing import Dict, List, Tuple, Set
from ortools.sat.python import cp_model

from horse_maze.types import Puzzle, Solution, Coord
from horse_maze.grid import build_adjacency, is_boundary

def solve_optimal(p: Puzzle, time_limit_s: float = 20.0) -> Solution:
    """
    Exact optimization with CP-SAT.

    IMPORTANT FIX:
    - r[v] must represent the TRUE set of cells reachable by the horse
      given the chosen blocks.
    - We enforce this using reachability closure constraints:
        r[u] AND passable[v] => r[v]
      for every directed adjacency edge u->v (including portals).
    """
    adj = build_adjacency(p)

    # Nodes are all non-wall cells
    nodes: List[Coord] = sorted(adj.keys())
    idx: Dict[Coord, int] = {rc: i for i, rc in enumerate(nodes)}
    n = len(nodes)

    model = cp_model.CpModel()

    # Reachable and block vars
    r_var = [model.NewBoolVar(f"r_{i}") for i in range(n)]
    b_var = [model.NewBoolVar(f"b_{i}") for i in range(n)]

    # passable[i] is a BoolVar: 1 if the cell can be walked on
    # (non-wall AND not blocked if air)
    passable = [model.NewBoolVar(f"passable_{i}") for i in range(n)]

    values: List[int] = [0] * n
    air_nodes: List[int] = []

    horse = p.horse
    horse_i = idx[horse]

    for rc, i in idx.items():
        cell = p.grid[rc[0]][rc[1]]
        values[i] = cell.value

        if cell.kind == "air":
            air_nodes.append(i)
            # passable = NOT blocked
            # passable + b = 1
            model.Add(passable[i] + b_var[i] == 1)
        else:
            # cannot block non-air
            model.Add(b_var[i] == 0)
            # always passable (since walls aren't in nodes at all)
            model.Add(passable[i] == 1)

        # Boundary open cells must NOT be reachable
        if is_boundary(p, rc):
            model.Add(r_var[i] == 0)

    # Horse must be reachable
    model.Add(r_var[horse_i] == 1)

    # Block budget
    model.Add(sum(b_var[i] for i in air_nodes) <= p.max_blocks)

    # Directed edges u -> v (including portal edges already in adj)
    arcs: List[Tuple[int, int]] = []
    for u in nodes:
        u_i = idx[u]
        for v in adj[u]:
            v_i = idx[v]
            arcs.append((u_i, v_i))

    # --- CRITICAL FIX: Reachability closure ---
    # If u is reachable and v is passable, then v is reachable.
    # r[u] + passable[v] - 1 <= r[v]
    for (u, v) in arcs:
        model.Add(r_var[u] + passable[v] - 1 <= r_var[v])

    # Objective: maximize score of all reachable cells
    model.Maximize(sum(values[i] * r_var[i] for i in range(n)))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return Solution(feasible=False, max_score=0, blocks=set(), reachable=set())

    blocks: Set[Coord] = set()
    reachable: Set[Coord] = set()

    for rc, i in idx.items():
        if solver.Value(r_var[i]) == 1:
            reachable.add(rc)
        if p.grid[rc[0]][rc[1]].kind == "air" and solver.Value(b_var[i]) == 1:
            blocks.add(rc)

    return Solution(
        feasible=True,
        max_score=int(solver.ObjectiveValue()),
        blocks=blocks,
        reachable=reachable,
    )
