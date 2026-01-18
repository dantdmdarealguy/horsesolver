from __future__ import annotations
import tkinter as tk
from typing import Dict, Tuple

from horse_maze.types import Puzzle, Solution, Coord
from horse_maze.verify import compute_reachable, score_region
from horse_maze.grid import is_boundary

CELL = 42  # pixel size per cell

def _cell_style(token: str) -> Dict[str, str]:
    # Basic palette; tweak as you like
    if token == "W":
        return {"fill": "#2b2b2b", "text": "white"}
    if token == "H":
        return {"fill": "#2b6cb0", "text": "white"}
    if token == "A":
        return {"fill": "#38a169", "text": "black"}
    if token == "C":
        return {"fill": "#e53e3e", "text": "white"}
    if token in {"E", "B", "BEE", "Bee"}:
        return {"fill": "#d69e2e", "text": "black"}
    if token.startswith("P"):
        return {"fill": "#805ad5", "text": "white"}
    if token == ".":
        return {"fill": "#f7fafc", "text": "black"}
    return {"fill": "#edf2f7", "text": "black"}

def show_gui(p: Puzzle, sol: Solution) -> None:
    # Compute true reachable region (so GUI always shows reality)
    region = compute_reachable(p, sol.blocks)
    computed_score = score_region(p, region)
    escaped = any(is_boundary(p, rc) for rc in region)

    root = tk.Tk()
    root.title("Horse Maze Solver")

    # Top info bar
    info = tk.Frame(root)
    info.pack(side=tk.TOP, fill=tk.X)

    msg = f"Score: {sol.max_score} (computed {computed_score}) | Blocks: {len(sol.blocks)}/{p.max_blocks}"
    if escaped:
        msg += " | WARNING: Horse can reach boundary!"
    label = tk.Label(info, text=msg, font=("Segoe UI", 12))
    label.pack(side=tk.LEFT, padx=10, pady=8)

    # Scrollable canvas
    outer = tk.Frame(root)
    outer.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(outer, width=min(1000, p.cols * CELL + 2), height=min(800, p.rows * CELL + 2), bg="white")
    canvas.grid(row=0, column=0, sticky="nsew")

    vbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
    hbar = tk.Scrollbar(outer, orient=tk.HORIZONTAL, command=canvas.xview)
    canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
    vbar.grid(row=0, column=1, sticky="ns")
    hbar.grid(row=1, column=0, sticky="ew")

    outer.grid_rowconfigure(0, weight=1)
    outer.grid_columnconfigure(0, weight=1)

    # Draw grid
    for r in range(p.rows):
        for c in range(p.cols):
            rc = (r, c)
            cell = p.grid[r][c]
            token = cell.token

            # Blocks override
            if rc in sol.blocks:
                token = "B"

            style = _cell_style(token if token != "B" else ".")
            x1, y1 = c * CELL, r * CELL
            x2, y2 = x1 + CELL, y1 + CELL

            # Fill
            fill = style["fill"]
            text_color = style["text"]

            # Make blocks obvious
            if token == "B":
                fill = "#111827"
                text_color = "white"

            rect = canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="#cbd5e0")

            # Outline enclosed region
            if rc in region and cell.kind != "wall" and token != "B":
                canvas.itemconfig(rect, outline="#00b5d8", width=3)

            # Mark boundary cells subtly
            if (r == 0 or r == p.rows - 1 or c == 0 or c == p.cols - 1) and cell.kind != "wall":
                # thin red edge to show "escape boundary"
                canvas.create_rectangle(x1+2, y1+2, x2-2, y2-2, outline="#f56565", width=1)

            # Text
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=token, fill=text_color, font=("Consolas", 12, "bold"))

    canvas.config(scrollregion=(0, 0, p.cols * CELL, p.rows * CELL))

    root.mainloop()
