from horse_maze.parser import parse_puzzle_file
from horse_maze.solver import solve_optimal
from horse_maze.render import render_solution

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python run.py <puzzle_file.txt>")
        raise SystemExit(2)

    path = sys.argv[1]
    puzzle = parse_puzzle_file(path)

    result = solve_optimal(puzzle)
    print(render_solution(puzzle, result))

if __name__ == "__main__":
    main()
