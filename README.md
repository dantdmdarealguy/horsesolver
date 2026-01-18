# Horse Maze Solver (Optimal Block Placement)

This project solves a grid puzzle:
- You place up to K Blocks on Air tiles
- Goal: enclose the Horse so it cannot reach any open edge tile
- Maximize points of all tiles enclosed with the horse

## Tokens (space-separated recommended)
H  = Horse (exactly one)
W  = Wall (impassable)
.  = Air (+1 if enclosed)
C  = Cherries (+3 if enclosed)
A  = Apples (+10 if enclosed)
E  = Bees (-5 if enclosed)

Portals:
P0..P9, Pa..Pz, PA..PZ (each worth +1 if enclosed)
Each portal label must appear exactly twice. Portals teleport between the pair.

Blocks:
You do not put blocks in the input. The solver outputs block placements.

## Input format
A text file:

rows cols
max_blocks
<row 0 tokens>
<row 1 tokens>
...
<row rows-1 tokens>

Tokens should be separated by spaces if using portals.

## Run
pip install -r requirements.txt

python run.py examples/demo.txt
OR
python run.py examples/demo.txt --gui
The gui is recommended

## Output
- Maximum score
- Block placements (row, col)
- Final grid rendering
