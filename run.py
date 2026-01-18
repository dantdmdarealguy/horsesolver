from horse_maze.parser import parse_puzzle_file
from horse_maze.solver import solve_optimal
from horse_maze.render import render_solution
from horse_maze.verify import verify_solution

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python run.py <puzzle_file.txt> [--gui]")
        raise SystemExit(2)

    path = sys.argv[1]
    use_gui = ("--gui" in sys.argv)

    puzzle = parse_puzzle_file(path)
    result = solve_optimal(puzzle)

    print(verify_solution(puzzle, result))
    print()
    print(render_solution(puzzle, result))

    if use_gui:
        from horse_maze.gui import show_gui
        show_gui(puzzle, result)

if __name__ == "__main__":
    main()
