from __future__ import annotations
from typing import List
from horse_maze.types import Puzzle, Solution

def render_solution(p: Puzzle, sol: Solution) -> str:
    if not sol.feasible:
        return "No feasible enclosure found under the given block limit."

    lines: List[str] = []
    lines.append(f"Max score: {sol.max_score}")
    lines.append(f"Blocks used: {len(sol.blocks)} / {p.max_blocks}")
    if sol.blocks:
        lines.append("Block placements (row, col):")
        for (r, c) in sorted(sol.blocks):
            lines.append(f"  - ({r}, {c})")
    else:
        lines.append("No blocks needed.")

    lines.append("")
    lines.append("Final grid (BLK = block, [] = enclosed cells):")

    # Render tokens; blocks override air only
    for r in range(p.rows):
        row_tokens: List[str] = []
        for c in range(p.cols):
            rc = (r, c)
            cell = p.grid[r][c]
            tok = cell.token

            if rc in sol.blocks:
                tok = "BLK"

            # Mark enclosed/reachable
            if rc in sol.reachable and cell.kind != "wall":
                tok = f"[{tok}]"
            else:
                tok = f" {tok} "

            row_tokens.append(tok)
        lines.append(" ".join(row_tokens))

    return "\n".join(lines)
