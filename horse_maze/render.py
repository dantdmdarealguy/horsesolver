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
    lines.append("")

    for r in range(p.rows):
        row_tokens: List[str] = []
        for c in range(p.cols):
            rc = (r, c)
            cell = p.grid[r][c]

            # Blocks override (you only place blocks on air)
            if rc in sol.blocks:
                row_tokens.append("B")
                continue

            tok = cell.token

            # Highlight only enclosed cells that "got points"
            # (i.e., are reachable AND have non-zero value)
            if rc in sol.reachable and cell.value != 0:
                tok = f"[{tok}]"

            row_tokens.append(tok)

        lines.append(" ".join(row_tokens))

    return "\n".join(lines)
