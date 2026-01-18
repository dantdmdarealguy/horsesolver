from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, Tuple, Optional, Set, List
from collections import deque

from PIL import Image, ImageDraw, ImageFont

from horse_maze.types import Puzzle, Solution, Coord
from horse_maze.grid import neighbors_4, is_boundary
from horse_maze.verify import compute_reachable, score_region

CELL = 42  # px

def _cell_style(token: str) -> Dict[str, str]:
    # palette
    if token == "W":
        return {"fill": "#2b2b2b", "text": "white"}
    if token == "H":
        return {"fill": "#2b6cb0", "text": "white"}
    if token == "A":
        return {"fill": "#38a169", "text": "black"}
    if token == "C":
        return {"fill": "#e53e3e", "text": "white"}
    if token in {"E", "BEE", "Bee"}:
        return {"fill": "#d69e2e", "text": "black"}
    if token.startswith("P"):
        return {"fill": "#805ad5", "text": "white"}
    if token == ".":
        return {"fill": "#f7fafc", "text": "black"}
    if token == "B":
        return {"fill": "#111827", "text": "white"}
    return {"fill": "#edf2f7", "text": "black"}

def _build_portal_pair(p: Puzzle) -> Dict[Coord, Coord]:
    pair: Dict[Coord, Coord] = {}
    for pid, coords in p.portals.items():
        a, b = coords
        pair[a] = b
        pair[b] = a
    return pair

def _passable(p: Puzzle, rc: Coord, blocks: Set[Coord]) -> bool:
    r, c = rc
    cell = p.grid[r][c]
    if cell.kind == "wall":
        return False
    if rc in blocks:
        return False
    return True

def _bfs_steps(p: Puzzle, blocks: Set[Coord]) -> List[Coord]:
    """
    Returns the order in which cells are discovered by BFS from the horse,
    including portal teleports as edges.
    """
    start = p.horse
    portal_pair = _build_portal_pair(p)

    q = deque([start])
    seen: Set[Coord] = {start}
    order: List[Coord] = [start]

    while q:
        u = q.popleft()

        # normal neighbors
        for v in neighbors_4(p, u):
            if _passable(p, v, blocks) and v not in seen:
                seen.add(v)
                q.append(v)
                order.append(v)

        # portal jump
        ur, uc = u
        if p.grid[ur][uc].kind == "portal":
            v = portal_pair.get(u)
            if v is not None and _passable(p, v, blocks) and v not in seen:
                seen.add(v)
                q.append(v)
                order.append(v)

    return order

class HorseMazeGUI:
    def __init__(self, p: Puzzle, sol: Solution):
        self.p = p
        self.sol = sol
        self.blocks = set(sol.blocks)

        # Always compute true region for correctness
        self.true_region = compute_reachable(p, self.blocks)
        self.true_score = score_region(p, self.true_region)
        self.escaped = any(is_boundary(p, rc) for rc in self.true_region)

        # Animation state
        self.bfs_order = _bfs_steps(p, self.blocks)
        self.anim_index = 0
        self.anim_running = False
        self.anim_region: Set[Coord] = set()  # region shown during animation

        # UI state toggles
        self.show_reachable_outline = tk.BooleanVar(value=True)
        self.show_boundary_marks = tk.BooleanVar(value=True)
        self.dim_walls = tk.BooleanVar(value=False)
        self.show_values = tk.BooleanVar(value=False)
        self.outline_scoring_only = tk.BooleanVar(value=False)

        self.speed_ms = tk.IntVar(value=40)  # animation delay

        self.root = tk.Tk()
        self.root.title("Horse Maze Solver")

        self._build_ui()
        self._redraw()

    def _build_ui(self):
        # Main layout: left controls + right canvas
        outer = tk.Frame(self.root)
        outer.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(outer, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y)

        right = tk.Frame(outer)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Info label top
        self.info_label = tk.Label(
            left,
            text="",
            font=("Segoe UI", 11),
            justify=tk.LEFT,
            wraplength=320,
        )
        self.info_label.pack(anchor="w", pady=(0, 10))

        # Toggles
        tk.Label(left, text="Overlays", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(5, 2))

        tk.Checkbutton(left, text="Reachable outline", variable=self.show_reachable_outline, command=self._redraw).pack(anchor="w")
        tk.Checkbutton(left, text="Boundary (escape) marks", variable=self.show_boundary_marks, command=self._redraw).pack(anchor="w")
        tk.Checkbutton(left, text="Dim walls", variable=self.dim_walls, command=self._redraw).pack(anchor="w")
        tk.Checkbutton(left, text="Show value labels", variable=self.show_values, command=self._redraw).pack(anchor="w")
        tk.Checkbutton(left, text="Outline scoring only", variable=self.outline_scoring_only, command=self._redraw).pack(anchor="w")

        # Actions
        tk.Label(left, text="Actions", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 2))

        tk.Button(left, text="Copy block placements", command=self._copy_blocks).pack(fill=tk.X, pady=2)
        tk.Button(left, text="Save solved grid (.txt)", command=self._save_grid).pack(fill=tk.X, pady=2)
        tk.Button(left, text="Save screenshot (.png)", command=self._save_png).pack(fill=tk.X, pady=2)

        # Animation controls
        tk.Label(left, text="Animation (BFS reach)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 2))

        row = tk.Frame(left)
        row.pack(fill=tk.X, pady=2)
        tk.Button(row, text="Start", command=self._anim_start).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        tk.Button(row, text="Pause", command=self._anim_pause).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(row, text="Reset", command=self._anim_reset).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        tk.Label(left, text="Speed (ms/step)").pack(anchor="w", pady=(8, 0))
        tk.Scale(left, from_=5, to=250, orient=tk.HORIZONTAL, variable=self.speed_ms).pack(fill=tk.X)

        # Inspector panel
        tk.Label(left, text="Inspector", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 2))
        self.inspect_text = tk.StringVar(value="Hover or click a cell.")
        self.inspect_label = tk.Label(left, textvariable=self.inspect_text, justify=tk.LEFT, font=("Consolas", 10), wraplength=320)
        self.inspect_label.pack(anchor="w")

        # Scrollable canvas
        self.canvas = tk.Canvas(right, bg="white")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vbar = tk.Scrollbar(right, orient=tk.VERTICAL, command=self.canvas.yview)
        hbar = tk.Scrollbar(right, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Bind hover/click
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Button-1>", self._on_click)

    def _current_region_for_display(self) -> Set[Coord]:
        # If anim is running or has progressed, show anim_region; else show full true region
        if self.anim_index > 0 or self.anim_running:
            return set(self.anim_region)
        return set(self.true_region)

    def _update_info_label(self):
        msg = (
            f"Score: {self.sol.max_score} (computed {self.true_score})\n"
            f"Blocks: {len(self.blocks)}/{self.p.max_blocks}\n"
            f"Grid: {self.p.rows} x {self.p.cols}"
        )
        if self.escaped:
            msg += "\nWARNING: Horse can reach boundary!"
        self.info_label.config(text=msg)

    def _redraw(self):
        self._update_info_label()
        self.canvas.delete("all")

        region = self._current_region_for_display()
        portal_pair = _build_portal_pair(self.p)

        width = self.p.cols * CELL
        height = self.p.rows * CELL

        for r in range(self.p.rows):
            for c in range(self.p.cols):
                rc = (r, c)
                cell = self.p.grid[r][c]
                tok = cell.token

                # blocks override
                if rc in self.blocks:
                    tok = "B"

                style = _cell_style(tok)

                fill = style["fill"]
                text_color = style["text"]

                # dim walls option
                if self.dim_walls.get() and tok == "W":
                    fill = "#4a5568"

                x1, y1 = c * CELL, r * CELL
                x2, y2 = x1 + CELL, y1 + CELL

                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="#cbd5e0", width=1)

                # boundary mark
                if self.show_boundary_marks.get():
                    if (r == 0 or r == self.p.rows - 1 or c == 0 or c == self.p.cols - 1) and cell.kind != "wall":
                        self.canvas.create_rectangle(x1+2, y1+2, x2-2, y2-2, outline="#f56565", width=1)

                # reachable outline
                if self.show_reachable_outline.get():
                    if rc in region and cell.kind != "wall" and tok != "B":
                        if self.outline_scoring_only.get():
                            if cell.value != 0:
                                self.canvas.itemconfig(rect, outline="#00b5d8", width=3)
                        else:
                            self.canvas.itemconfig(rect, outline="#00b5d8", width=3)

                # token text
                self.canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=tok,
                    fill=text_color,
                    font=("Consolas", 12, "bold"),
                    )

                # value overlay (small)
                if self.show_values.get() and tok not in {"W", "B"}:
                    v = cell.value
                    if v != 0:
                        self.canvas.create_text(
                            x2 - 4,
                            y1 + 4,
                            text=f"{v:+d}",
                            anchor="ne",
                            fill="#1a202c" if tok != "W" else "white",
                            font=("Consolas", 8),
                            )

        # Optional: draw portal links (tiny line) for clarity
        # Only between the portal pair, once
        drawn = set()
        for a, b in portal_pair.items():
            if (b, a) in drawn:
                continue
            drawn.add((a, b))
            ar, ac = a
            br, bc = b
            ax, ay = ac * CELL + CELL/2, ar * CELL + CELL/2
            bx, by = bc * CELL + CELL/2, br * CELL + CELL/2
            # faint line
            self.canvas.create_line(ax, ay, bx, by, fill="#9f7aea", width=2, dash=(4, 4))

        self.canvas.config(scrollregion=(0, 0, width, height))

    def _xy_to_cell(self, event) -> Optional[Coord]:
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        c = x // CELL
        r = y // CELL
        if 0 <= r < self.p.rows and 0 <= c < self.p.cols:
            return (r, c)
        return None

    def _describe_cell(self, rc: Coord) -> str:
        r, c = rc
        cell = self.p.grid[r][c]
        tok = cell.token
        if rc in self.blocks:
            tok = "B"

        region = self._current_region_for_display()
        reachable_now = (rc in region)
        reachable_true = (rc in self.true_region)

        lines = []
        lines.append(f"pos: ({r}, {c})")
        lines.append(f"token: {tok}")
        lines.append(f"kind: {cell.kind}")
        lines.append(f"value: {cell.value:+d}")
        lines.append(f"blocked: {'yes' if rc in self.blocks else 'no'}")
        lines.append(f"reachable (shown): {'yes' if reachable_now else 'no'}")
        lines.append(f"reachable (true): {'yes' if reachable_true else 'no'}")
        lines.append(f"boundary: {'yes' if is_boundary(self.p, rc) else 'no'}")

        if cell.kind == "portal":
            pair = _build_portal_pair(self.p).get(rc)
            lines.append(f"portal -> {pair}")

        return "\n".join(lines)

    def _on_hover(self, event):
        rc = self._xy_to_cell(event)
        if rc is None:
            self.inspect_text.set("Hover or click a cell.")
            return
        self.inspect_text.set(self._describe_cell(rc))

    def _on_click(self, event):
        rc = self._xy_to_cell(event)
        if rc is None:
            return
        # lock the inspector text on click
        self.inspect_text.set(self._describe_cell(rc))

    def _copy_blocks(self):
        if not self.blocks:
            text = "(no blocks)"
        else:
            # same format as console list
            text = "\n".join(f"({r}, {c})" for (r, c) in sorted(self.blocks))

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copied", "Block placements copied to clipboard.")

    def _save_grid(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save solved grid",
        )
        if not path:
            return

        # Save in reloadable format (same header + grid with B inserted)
        lines: List[str] = []
        lines.append(f"{self.p.rows} {self.p.cols}")
        lines.append(str(self.p.max_blocks))

        for r in range(self.p.rows):
            row = []
            for c in range(self.p.cols):
                rc = (r, c)
                if rc in self.blocks:
                    row.append("B")
                else:
                    row.append(self.p.grid[r][c].token)
            lines.append(" ".join(row))

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        messagebox.showinfo("Saved", f"Saved solved grid to:\n{path}")

    def _save_png(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
            title="Save screenshot (rendered)",
        )
        if not path:
            return

        # Render an image of the FULL grid (not just visible viewport)
        region = self._current_region_for_display()
        img_w = self.p.cols * CELL
        img_h = self.p.rows * CELL

        img = Image.new("RGB", (img_w, img_h), "white")
        draw = ImageDraw.Draw(img)

        # Use default font (works everywhere)
        try:
            font_main = ImageFont.truetype("consola.ttf", 16)
            font_small = ImageFont.truetype("consola.ttf", 10)
        except Exception:
            font_main = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # helper to center text
        def draw_centered_text(x1, y1, x2, y2, text, fill, font):
            w, h = draw.textbbox((0, 0), text, font=font)[2:]
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            draw.text((cx - w // 2, cy - h // 2), text, fill=fill, font=font)

        for r in range(self.p.rows):
            for c in range(self.p.cols):
                rc = (r, c)
                cell = self.p.grid[r][c]
                tok = "B" if rc in self.blocks else cell.token

                style = _cell_style(tok)
                fill = style["fill"]
                text_color = style["text"]

                if self.dim_walls.get() and tok == "W":
                    fill = "#4a5568"

                x1, y1 = c * CELL, r * CELL
                x2, y2 = x1 + CELL, y1 + CELL

                draw.rectangle([x1, y1, x2, y2], fill=fill, outline="#cbd5e0", width=1)

                # boundary marks
                if self.show_boundary_marks.get():
                    if (r == 0 or r == self.p.rows - 1 or c == 0 or c == self.p.cols - 1) and cell.kind != "wall":
                        draw.rectangle([x1+2, y1+2, x2-2, y2-2], outline="#f56565", width=1)

                # reachable outline
                if self.show_reachable_outline.get():
                    if rc in region and cell.kind != "wall" and tok != "B":
                        do_outline = True
                        if self.outline_scoring_only.get():
                            do_outline = (cell.value != 0)
                        if do_outline:
                            draw.rectangle([x1, y1, x2, y2], outline="#00b5d8", width=3)

                draw_centered_text(x1, y1, x2, y2, tok, text_color, font_main)

                # value overlay
                if self.show_values.get() and tok not in {"W", "B"}:
                    v = cell.value
                    if v != 0:
                        s = f"{v:+d}"
                        draw.text((x2 - 4, y1 + 2), s, fill="#1a202c", font=font_small, anchor="ra")

        img.save(path, "PNG")
        messagebox.showinfo("Saved", f"Saved PNG to:\n{path}")

    # ---- Animation controls ----
    def _anim_start(self):
        if self.anim_running:
            return
        self.anim_running = True
        if self.anim_index == 0:
            self.anim_region = set()
        self._anim_tick()

    def _anim_pause(self):
        self.anim_running = False

    def _anim_reset(self):
        self.anim_running = False
        self.anim_index = 0
        self.anim_region = set()
        self._redraw()

    def _anim_tick(self):
        if not self.anim_running:
            return

        if self.anim_index < len(self.bfs_order):
            rc = self.bfs_order[self.anim_index]
            self.anim_region.add(rc)
            self.anim_index += 1
            self._redraw()
            self.root.after(int(self.speed_ms.get()), self._anim_tick)
        else:
            self.anim_running = False
            # leave the full discovered region showing

    def run(self):
        self.root.mainloop()

def show_gui(p: Puzzle, sol: Solution) -> None:
    app = HorseMazeGUI(p, sol)
    app.run()
