from horse_maze.parser import parse_puzzle_file
from horse_maze.solver import solve_optimal
from horse_maze.render import render_solution
from horse_maze.verify import verify_solution

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run.py <puzzle_file.txt> [--gui | --guiplay]")
        raise SystemExit(2)

    path = sys.argv[1]
    use_gui = ("--gui" in sys.argv)
    use_guiplay = ("--guiplay" in sys.argv)

    if use_gui and use_guiplay:
        print("Pick one: --gui OR --guiplay (not both).")
        raise SystemExit(2)

    puzzle = parse_puzzle_file(path)

    # CLI bot-solve (default)
    if not use_gui and not use_guiplay:
        result = solve_optimal(puzzle)
        print(verify_solution(puzzle, result))
        print()
        print(render_solution(puzzle, result))
        return

    # Bot-solve GUI
    if use_gui:
        result = solve_optimal(puzzle)
        print(verify_solution(puzzle, result))
        print()
        print(render_solution(puzzle, result))
        from horse_maze.gui import show_gui
        show_gui(puzzle, result, mode="solve")
        return

    # Playable GUI
    if use_guiplay:
        from horse_maze.gui import show_gui
        # no solve; user plays
        show_gui(puzzle, None, mode="play")
        return

if __name__ == "__main__":
    main()
