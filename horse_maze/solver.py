from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
from ortools.sat.python import cp_model

from horse_maze.types import Puzzle, Solution, Coord
from horse_maze.grid import build_adjacency, is_boundary

def solve_optimal(p: Puzzle, time_limit_s: float = 20.0) -> Solution:
    """
    Exact optimization with CP-SAT:

    Variables:
      r[v] = 1 if cell v is reachable from the horse (enclosed region)
      b[v] = 1 if we place a block on air cell v (removes it)
      f[u->v] = flow for connectivity enforcement (single-commodity flow)

    Constraints:
      - r[horse] = 1
      - boundary open cells must have r = 0
      - air cells: r[v] <= 1 - b[v]
      - non-air cells: b[v] = 0
      - sum b[v] <= max_blocks
      - flow conservation ensures connectivity of all reachable nodes from horse

    Objective:
      maximize sum(value[v] * r[v])
    """
    adj = build_adjacency(p)

    # Universe of nodes (non-walls)
    nodes: List[Coord] = sorted(adj.keys())
    idx: Dict[Coord, int] = {rc: i for i, rc in enumerate(nodes)}
    n = len(nodes)
    horse = p.horse

    # Quick sanity: if any boundary cell is horse-reachable without walls? Not relevant here.
    # We'll let the solver decide blocks, but boundary reachable is forbidden via constraints.

    model = cp_model.CpModel()

    # Decision vars
    r_var = [model.NewBoolVar(f"r_{i}") for i in range(n)]  # reachable/enclosed
    b_var = [model.NewBoolVar(f"b_{i}") for i in range(n)]  # block placed (only meaningful for air)

    # Identify air vs non-air and boundary nodes
    air_nodes: List[int] = []
    boundary_nodes: List[int] = []
    values: List[int] = [0] * n

    for rc, i in idx.items():
        cell = p.grid[rc[0]][rc[1]]
        values[i] = cell.value

        if cell.kind == "air":
            air_nodes.append(i)
        else:
            # cannot place blocks on non-air
            model.Add(b_var[i] == 0)

        if is_boundary(p, rc):
            # Boundary non-wall cells must not be reachable (or horse could leave)
            boundary_nodes.append(i)
            model.Add(r_var[i] == 0)

    # horse must be reachable
    model.Add(r_var[idx[horse]] == 1)

    # Air block implies not reachable
    for i in air_nodes:
        # r_i <= 1 - b_i
        model.Add(r_var[i] + b_var[i] <= 1)

    # Block budget
    model.Add(sum(b_var[i] for i in air_nodes) <= p.max_blocks)

    # Build directed arcs for flow
    arcs: List[Tuple[int, int]] = []
    for u in nodes:
        u_i = idx[u]
        for v in adj[u]:
            v_i = idx[v]
            arcs.append((u_i, v_i))

    # Flow variables
    # Upper bound on total flow is at most (n-1), one unit per reachable non-horse node.
    M = n

    f = {}
    for (u, v) in arcs:
        f[(u, v)] = model.NewIntVar(0, M, f"f_{u}_{v}")
        # flow can only go between reachable nodes
        model.Add(f[(u, v)] <= M * r_var[u])
        model.Add(f[(u, v)] <= M * r_var[v])

    horse_i = idx[horse]

    # Flow conservation:
    # For each node i != horse: inflow - outflow = r[i]
    # For horse: outflow - inflow = sum_{i!=horse} r[i]
    total_reachable_except_horse = model.NewIntVar(0, n - 1, "total_reachable_except_horse")
    model.Add(total_reachable_except_horse == sum(r_var[i] for i in range(n) if i != horse_i))

    for i in range(n):
        inflow = []
        outflow = []
        for (u, v) in arcs:
            if v == i:
                inflow.append(f[(u, v)])
            if u == i:
                outflow.append(f[(u, v)])

        if i == horse_i:
            model.Add(sum(outflow) - sum(inflow) == total_reachable_except_horse)
        else:
            model.Add(sum(inflow) - sum(outflow) == r_var[i])

    # Objective: maximize score of reachable region
    model.Maximize(sum(values[i] * r_var[i] for i in range(n)))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = 8  # parallel
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

    max_score = int(solver.ObjectiveValue())

    return Solution(feasible=True, max_score=max_score, blocks=blocks, reachable=reachable)
