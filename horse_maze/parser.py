from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from horse_maze.types import Cell, Puzzle, Coord

_ALLOWED_PORTAL_LABELS = (
        [str(d) for d in range(10)]
        + [chr(c) for c in range(ord("a"), ord("z") + 1)]
        + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
)

def _is_portal_token(tok: str) -> bool:
    return len(tok) == 2 and tok[0] == "P" and tok[1] in _ALLOWED_PORTAL_LABELS

def _cell_from_token(tok: str) -> Cell:
    # Normalize some aliases
    if tok in {".", "AIR", "_", "a"}:
        return Cell(token=tok, kind="air", value=1)

    if tok == "W":
        return Cell(token=tok, kind="wall", value=0)

    if tok == "H":
        return Cell(token=tok, kind="horse", value=0)

    # Items
    if tok == "C":
        return Cell(token=tok, kind="item", value=3)
    if tok == "A":
        return Cell(token=tok, kind="item", value=10)
    # Bees (negative)
    if tok in {"E", "B", "BEE", "Bee"}:
        return Cell(token=tok, kind="item", value=-5)

    # Portals
    if _is_portal_token(tok):
        return Cell(token=tok, kind="portal", value=1, portal_id=tok[1])

    raise ValueError(f"Invalid token: {tok!r}")

def parse_puzzle_lines(lines: List[str]) -> Puzzle:
    # Strip comments and blank lines
    cleaned: List[str] = []
    for ln in lines:
        s = ln.split("#", 1)[0].strip()
        if s:
            cleaned.append(s)

    if len(cleaned) < 3:
        raise ValueError("Not enough lines. Expected: 'rows cols', 'max_blocks', then grid rows.")

    # Header
    r_c = cleaned[0].split()
    if len(r_c) != 2:
        raise ValueError("First line must be: rows cols")
    rows = int(r_c[0])
    cols = int(r_c[1])

    max_blocks = int(cleaned[1])

    grid_lines = cleaned[2:]
    if len(grid_lines) != rows:
        raise ValueError(f"Expected {rows} grid rows, got {len(grid_lines)}")

    grid: List[List[Cell]] = []
    portals: Dict[str, List[Coord]] = {}
    horse: Optional[Coord] = None

    for r in range(rows):
        tokens = grid_lines[r].split()
        if len(tokens) != cols:
            raise ValueError(f"Row {r} must have {cols} tokens (space-separated). Got {len(tokens)}")

        row_cells: List[Cell] = []
        for c, tok in enumerate(tokens):
            cell = _cell_from_token(tok)
            row_cells.append(cell)

            if cell.kind == "horse":
                if horse is not None:
                    raise ValueError("Multiple horses found. Exactly one 'H' is required.")
                horse = (r, c)

            if cell.kind == "portal":
                assert cell.portal_id is not None
                portals.setdefault(cell.portal_id, []).append((r, c))

        grid.append(row_cells)

    if horse is None:
        raise ValueError("No horse found. Exactly one 'H' is required.")

    # Validate portals: each label must appear exactly twice
    for pid, coords in portals.items():
        if len(coords) != 2:
            raise ValueError(
                f"Portal P{pid} must appear exactly twice, but appears {len(coords)} time(s)."
            )

    # If horse is on the boundary and not a wall, it's impossible (horse can leave immediately)
    hr, hc = horse
    if hr == 0 or hr == rows - 1 or hc == 0 or hc == cols - 1:
        # Still may be solvable if that boundary cell is considered "open edge cell",
        # which would violate enclosure immediately. We'll treat it as invalid puzzle.
        raise ValueError("Horse is on the grid boundary; that violates the 'cannot leave' rule.")

    return Puzzle(rows=rows, cols=cols, max_blocks=max_blocks, grid=grid, horse=horse, portals=portals)

def parse_puzzle_file(path: str) -> Puzzle:
    with open(path, "r", encoding="utf-8") as f:
        return parse_puzzle_lines(f.readlines())
