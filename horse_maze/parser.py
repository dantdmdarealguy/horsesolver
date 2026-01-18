from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import re

import json
import re

from horse_maze.types import Puzzle, Cell, Coord

_PORTAL_ID_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _is_portal_token(tok: str) -> bool:
    return len(tok) == 2 and tok[0] == "P" and tok[1] in _PORTAL_ID_CHARS

def _cell_from_token(tok: str) -> Cell:
    # Walls
    if tok in {"W", "~"}:
        return Cell(token="W", kind="wall", value=0)

    # Saved blocks should load as impassable
    if tok == "B":
        return Cell(token="B", kind="wall", value=0)

    # Air
    if tok in {".", "AIR", "_"}:
        return Cell(token=".", kind="air", value=1)

    # Horse counts as +1 (your rule)
    if tok == "H":
        return Cell(token="H", kind="horse", value=1)

    # Items
    if tok == "C":
        return Cell(token="C", kind="item", value=3)
    if tok == "A":
        return Cell(token="A", kind="item", value=10)
    if tok in {"E", "BEE", "Bee"}:
        return Cell(token="E", kind="item", value=-5)

    # Portals
    if _is_portal_token(tok):
        return Cell(token=tok, kind="portal", value=1, portal_id=tok[1])

    raise ValueError(f"Invalid token: {tok!r}")

def parse_puzzle_file(path: str) -> Puzzle:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        raise ValueError("Empty puzzle file.")

    # 1) Expanded format: first line like "rows cols"
    first_line = raw.splitlines()[0].strip()
    if re.match(r"^\d+\s+\d+$", first_line):
        lines = [ln.rstrip("\n") for ln in raw.splitlines()]
        return _parse_expanded(lines)

    # 2) One-line map/budget format (JSON-ish)
    if '"map"' in raw and '"budget"' in raw:
        return _parse_map_budget_line(raw)

    # 3) Legacy compact format with max_blocks on first line (optional if you still want it)
    # Allow pasting strings with literal "\n"
    raw2 = raw.replace("\\n", "\n")
    lines = [ln.rstrip("\n") for ln in raw2.splitlines() if ln.strip()]
    if lines and re.match(r"^\d+$", lines[0].strip()):
        return _parse_compact(lines)

    raise ValueError(
        "Unrecognized puzzle format.\n"
        "Supported:\n"
        " - Expanded: rows cols / budget / grid tokens\n"
        " - One-line: \"map\":\"...\",\"budget\":13\n"
    )

def _parse_expanded(lines: List[str]) -> Puzzle:
    # rows cols
    r0 = lines[0].split()
    rows, cols = int(r0[0]), int(r0[1])

    if len(lines) < 2:
        raise ValueError("Missing max_blocks line.")
    max_blocks = int(lines[1].strip())

    grid_lines = lines[2:]
    if len(grid_lines) != rows:
        raise ValueError(f"Expected {rows} grid rows, got {len(grid_lines)}.")

    grid: List[List[Cell]] = []
    horse: Optional[Coord] = None
    portals: Dict[str, List[Coord]] = {}

    for r in range(rows):
        toks = grid_lines[r].split()
        if len(toks) != cols:
            raise ValueError(f"Row {r}: expected {cols} tokens, got {len(toks)}.")
        row_cells: List[Cell] = []
        for c, tok in enumerate(toks):
            cell = _cell_from_token(tok)
            row_cells.append(cell)
            if cell.kind == "horse":
                if horse is not None:
                    raise ValueError("Multiple horses found.")
                horse = (r, c)
            if cell.kind == "portal":
                portals.setdefault(cell.portal_id, []).append((r, c))
        grid.append(row_cells)

    if horse is None:
        raise ValueError("No horse (H) found.")

    _validate_portals(portals)

    return Puzzle(rows=rows, cols=cols, max_blocks=max_blocks, grid=grid, horse=horse, portals={k: v for k, v in portals.items()})

def _parse_compact(lines: List[str]) -> Puzzle:
    """
    Compact format:

    Option A (recommended):
        <max_blocks>
        <grid line 0>
        <grid line 1>
        ...

    Option B:
        <grid line 0>
        <grid line 1>
        ...
      (NOT supported unless you tell me what max_blocks should default to.)
    """
    # If first line is a plain int, treat it as max_blocks
    if re.match(r"^\s*\d+\s*$", lines[0]):
        max_blocks = int(lines[0].strip())
        grid_lines = lines[1:]
    else:
        raise ValueError(
            "Compact format requires max_blocks on the first line.\n"
            "Example:\n"
            "13\n"
            "2~~~~~~1~~~~~~0\n"
            "~~~~~....1~~~~~\n"
            "..."
        )

    if not grid_lines:
        raise ValueError("Missing compact grid lines after max_blocks.")

    rows = len(grid_lines)
    cols = len(grid_lines[0])

    # Validate rectangle
    for i, ln in enumerate(grid_lines):
        if len(ln) != cols:
            raise ValueError(f"Compact grid must be rectangular. Line {i} has length {len(ln)} but expected {cols}.")

    grid: List[List[Cell]] = []
    horse: Optional[Coord] = None
    portals: Dict[str, List[Coord]] = {}

    for r in range(rows):
        row_cells: List[Cell] = []
        for c, ch in enumerate(grid_lines[r]):
            tok = _compact_char_to_token(ch)
            cell = _cell_from_token(tok)
            row_cells.append(cell)

            if cell.kind == "horse":
                if horse is not None:
                    raise ValueError("Multiple horses found.")
                horse = (r, c)
            if cell.kind == "portal":
                portals.setdefault(cell.portal_id, []).append((r, c))
        grid.append(row_cells)

    if horse is None:
        raise ValueError("No horse (H) found.")

    _validate_portals(portals)

    return Puzzle(rows=rows, cols=cols, max_blocks=max_blocks, grid=grid, horse=horse, portals={k: v for k, v in portals.items()})

def _compact_char_to_token(ch: str) -> str:
    if ch == "~":
        return "W"
    if ch == ".":
        return "."
    if ch in {"W", "H", "A", "C", "E", "B"}:
        return ch
    # portals: 0-9, a-z, A-Z
    if ch in _PORTAL_ID_CHARS:
        return "P" + ch
    raise ValueError(f"Invalid compact character: {ch!r}")

def _parse_map_budget_line(raw: str) -> Puzzle:
    """
    Accepts a single-line format like:
      "map":"2~~~~\\n...","budget":13
    (all on one line)

    We'll convert it into proper JSON, parse it, then decode the compact grid.
    """
    # Make it valid JSON if it's missing outer braces
    s = raw.strip()
    if not s.startswith("{"):
        s = "{" + s
    if not s.endswith("}"):
        s = s + "}"

    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        # Fallback: try to pull fields with regex (more forgiving)
        m_map = re.search(r'"map"\s*:\s*"((?:\\.|[^"])*)"', raw)
        m_budget = re.search(r'"budget"\s*:\s*(\d+)', raw)
        if not m_map or not m_budget:
            raise ValueError("Could not parse map/budget line as JSON or via regex.")
        map_str = m_map.group(1)
        budget = int(m_budget.group(1))
    else:
        if "map" not in obj or "budget" not in obj:
            raise ValueError('Map/budget line must include keys "map" and "budget".')
        map_str = obj["map"]
        budget = int(obj["budget"])

    # map_str might contain literal \n escapes. Decode them.
    if isinstance(map_str, str):
        map_text = map_str.encode("utf-8").decode("unicode_escape")
    else:
        raise ValueError('"map" must be a string.')

    # Normalize line endings and strip empty edges
    grid_lines = [ln.rstrip("\r") for ln in map_text.splitlines()]
    while grid_lines and not grid_lines[0].strip():
        grid_lines.pop(0)
    while grid_lines and not grid_lines[-1].strip():
        grid_lines.pop()

    # Build a lines list compatible with _parse_compact (expects first line budget)
    lines = [str(budget)] + grid_lines
    return _parse_compact(lines)

def _validate_portals(portals: Dict[str, List[Coord]]) -> None:
    for pid, coords in portals.items():
        if len(coords) != 2:
            raise ValueError(f"Portal P{pid} must appear exactly twice; found {len(coords)}.")
