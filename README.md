# Horse Maze Solver (Optimal + Playable)

This project solves (and lets you play) a grid puzzle:

- **You may place up to K Blocks** on Air tiles.
- Goal: **enclose the Horse** so it cannot reach any **open boundary cell** (because it could leave the grid).
- Score is the total value of **all tiles reachable from the Horse** once enclosed (including Air, items, portals).
- Portals teleport between their paired locations.

---

## Tokens (space-separated recommended)

Required:
- `H` = Horse (exactly one)
- `W` = Wall (impassable)
- `.` = Air (+1 if enclosed)

Items:
- `C` = Cherries (+3 if enclosed)
- `A` = Apples (+10 if enclosed)
- `E` = Bees (-5 if enclosed)

Portals:
- `P0..P9`, `Pa..Pz`, `PA..PZ` (each worth +1 if enclosed)
- Each portal label must appear **exactly twice** (paired teleport).

Blocks:
- The solver outputs Blocks.
- In saved grids, Blocks are written as `B` (impassable).  
  (In play mode, you place/remove `B` on Air by clicking.)

---

## Input format (text file)

rows cols
max_blocks
<row 0 tokens>
<row 1 tokens>
...
<row rows-1 tokens>

Tokens should be space-separated (especially important for portals like `P0`).

---

## Install

pip install -r requirements.txt

---

## Run modes

### 1) Bot solver (CLI output)
python run.py examples/demo.txt

Outputs:
- Validity check (enclosed + score matches simulation)
- Max score
- Block placements
- Final grid (with `[]` around enclosed scoring tiles)

### 2) Bot solver GUI (recommended)
python run.py examples/demo.txt --gui

Shows:
- Colored grid
- Reachable/enclosed region outline
- Portal links
- Inspector panel (hover/click)
- Export tools: save grid, save PNG, copy blocks
- BFS reachability animation
- Escape path checker/overlay

### 3) Playable GUI (manual block placement)
python run.py examples/demo.txt --guiplay

You can:
- **Left click Air (`.`)** to place/remove a Block (`B`)
- Max blocks enforced (won’t let you exceed K)
- Live score + enclosure status
- Escape path checker (highlights an example shortest escape path if one exists)
- All the same overlays/tools as the solver GUI

---

## Notes

- Enclosure rule: the horse must not be able to reach **any non-wall boundary cell**.
- Score is computed from the horse’s **true reachable region** (including portals).