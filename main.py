import sys
import time
import tracemalloc


class Node:
    def __init__(self, state, parent, action, path_cost=0, depth=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.path_cost = path_cost
        self.depth = depth


class StackFrontier:
    def __init__(self):
        self.frontier = []

    def add(self, node):
        self.frontier.append(node)

    def contains_state(self, state):
        return any(node.state == state for node in self.frontier)

    def empty(self):
        return len(self.frontier) == 0

    def remove(self):
        if self.empty():
            raise Exception("empty frontier")
        return self.frontier.pop()


class QueueFrontier(StackFrontier):
    def remove(self):
        if self.empty():
            raise Exception("empty frontier")
        return self.frontier.pop(0)


class PriorityFrontier:
    def __init__(self):
        self.frontier = []

    def add(self, node):
        self.frontier.append(node)

    def empty(self):
        return len(self.frontier) == 0

    def remove(self):
        if self.empty():
            raise Exception("empty frontier")

        lowest_index = 0

        for index in range(1, len(self.frontier)):
            if self.frontier[index].path_cost < self.frontier[lowest_index].path_cost:
                lowest_index = index

        return self.frontier.pop(lowest_index)


class Maze:
    def __init__(self, filename):
        with open(filename, encoding="utf-8") as file:
            contents = file.read()

        if contents.count("A") != 1:
            raise Exception("maze must have exactly one start point")

        if contents.count("B") != 1:
            raise Exception("maze must have exactly one goal")

        contents = contents.splitlines()
        self.height = len(contents)
        self.width = max(len(line) for line in contents)
        self.walls = []

        for i in range(self.height):
            row = []

            for j in range(self.width):
                try:
                    if contents[i][j] == "A":
                        self.start = (i, j)
                        row.append(False)
                    elif contents[i][j] == "B":
                        self.goal = (i, j)
                        row.append(False)
                    elif contents[i][j] == " ":
                        row.append(False)
                    else:
                        row.append(True)
                except IndexError:
                    row.append(True)

            self.walls.append(row)

        self.solution = None
        self.solution_cost = None
        self.depth_limit_used = None
        self.num_explored = 0
        self.explored = set()

    def print(self):
        solution = self.solution[1] if self.solution is not None else None

        print()

        for i, row in enumerate(self.walls):
            for j, wall in enumerate(row):
                if wall:
                    print("█", end="")
                elif (i, j) == self.start:
                    print("A", end="")
                elif (i, j) == self.goal:
                    print("B", end="")
                elif solution is not None and (i, j) in solution:
                    print("*", end="")
                else:
                    print(" ", end="")

            print()

        print()

    def neighbors(self, state):
        row, col = state

        candidates = [
            ("up", (row - 1, col)),
            ("down", (row + 1, col)),
            ("left", (row, col - 1)),
            ("right", (row, col + 1))
        ]

        result = []

        for action, (r, c) in candidates:
            if 0 <= r < self.height and 0 <= c < self.width and not self.walls[r][c]:
                result.append((action, (r, c)))

        return result

    def step_cost(self, state):
        return 1

    def save_solution(self, node):
        actions = []
        cells = []
        self.solution_cost = node.path_cost

        while node.parent is not None:
            actions.append(node.action)
            cells.append(node.state)
            node = node.parent

        actions.reverse()
        cells.reverse()
        self.solution = (actions, cells)

    def solve_uniform_cost(self):
        self.num_explored = 0
        self.explored = set()

        start = Node(self.start, None, None, 0, 0)
        frontier = PriorityFrontier()
        frontier.add(start)
        best_cost = {self.start: 0}

        while True:
            if frontier.empty():
                raise Exception("no solution")

            node = frontier.remove()

            if node.path_cost != best_cost.get(node.state):
                continue

            if node.state in self.explored:
                continue

            self.num_explored += 1

            if node.state == self.goal:
                self.save_solution(node)
                return

            self.explored.add(node.state)

            for action, state in self.neighbors(node.state):
                new_cost = node.path_cost + self.step_cost(state)

                if state not in best_cost or new_cost < best_cost[state]:
                    best_cost[state] = new_cost
                    child = Node(state, node, action, new_cost, node.depth + 1)
                    frontier.add(child)

    def run_depth_limited(self, limit):
        start = Node(self.start, None, None, 0, 0)
        frontier = StackFrontier()
        frontier.add(start)
        explored = set()
        best_depth = {self.start: 0}
        num_explored = 0

        while not frontier.empty():
            node = frontier.remove()

            if node.depth != best_depth.get(node.state):
                continue

            num_explored += 1

            if node.state == self.goal:
                return node, num_explored, explored

            explored.add(node.state)

            if node.depth >= limit:
                continue

            for action, state in reversed(self.neighbors(node.state)):
                new_depth = node.depth + 1

                if state not in best_depth or new_depth < best_depth[state]:
                    best_depth[state] = new_depth
                    child = Node(state, node, action, node.path_cost + 1, new_depth)
                    frontier.add(child)

        return None, num_explored, explored

    def solve_depth_limited(self, limit):
        if limit < 0:
            raise ValueError("the depth limit cannot be negative")

        node, count, explored = self.run_depth_limited(limit)
        self.num_explored = count
        self.explored = explored
        self.depth_limit_used = limit

        if node is None:
            raise Exception(f"no solution within depth limit {limit}")

        self.save_solution(node)

    def solve_iterative_deepening(self):
        total_explored = 0
        all_explored = set()
        number_of_free_cells = sum(
            1
            for row in self.walls
            for wall in row
            if not wall
        )
        maximum_depth = number_of_free_cells - 1

        for limit in range(maximum_depth + 1):
            node, count, explored = self.run_depth_limited(limit)
            total_explored += count
            all_explored.update(explored)

            if node is not None:
                self.num_explored = total_explored
                self.explored = all_explored
                self.depth_limit_used = limit
                self.save_solution(node)
                return

        raise Exception("no solution")

    def solve(self, algorithm, depth_limit=None):
        self.solution = None
        self.solution_cost = None
        self.depth_limit_used = None

        if algorithm == "ucs":
            self.solve_uniform_cost()
        elif algorithm == "dls":
            if depth_limit is None:
                raise ValueError("DLS requires a depth limit")
            self.solve_depth_limited(depth_limit)
        elif algorithm == "ids":
            self.solve_iterative_deepening()
        else:
            raise ValueError("invalid algorithm: use ucs, dls or ids")

    def output_image(self, filename, show_solution=True, show_explored=False):
        from PIL import Image, ImageDraw

        cell_size = 50
        cell_border = 2

        image = Image.new(
            "RGBA",
            (self.width * cell_size, self.height * cell_size),
            "black"
        )

        draw = ImageDraw.Draw(image)
        solution = self.solution[1] if self.solution is not None else None

        for i, row in enumerate(self.walls):
            for j, wall in enumerate(row):
                if wall:
                    fill = (40, 40, 40)
                elif (i, j) == self.start:
                    fill = (255, 0, 0)
                elif (i, j) == self.goal:
                    fill = (0, 171, 28)
                elif solution is not None and show_solution and (i, j) in solution:
                    fill = (220, 235, 113)
                elif show_explored and (i, j) in self.explored:
                    fill = (212, 97, 85)
                else:
                    fill = (237, 240, 252)

                draw.rectangle(
                    [
                        (
                            j * cell_size + cell_border,
                            i * cell_size + cell_border
                        ),
                        (
                            (j + 1) * cell_size - cell_border,
                            (i + 1) * cell_size - cell_border
                        )
                    ],
                    fill=fill
                )

        image.save(filename)
        image.show()


if len(sys.argv) < 3:
    sys.exit(
        "Usage:\n"
        "python main.py maze.txt ucs\n"
        "python main.py maze.txt dls limit\n"
        "python main.py maze.txt ids"
    )

filename = sys.argv[1]
algorithm = sys.argv[2].lower()
depth_limit = None

if algorithm == "dls":
    if len(sys.argv) != 4:
        sys.exit("DLS requires a depth limit")

    try:
        depth_limit = int(sys.argv[3])
    except ValueError:
        sys.exit("the depth limit must be an integer")
elif len(sys.argv) != 3:
    sys.exit("invalid number of arguments")

if algorithm not in ("ucs", "dls", "ids"):
    sys.exit("invalid algorithm: use ucs, dls or ids")

maze = Maze(filename)

print("Maze:")
maze.print()
print("Algorithm:", algorithm.upper())
print("Solving...")

tracemalloc.start()
start_time = time.perf_counter()

try:
    maze.solve(algorithm, depth_limit)
except Exception as error:
    tracemalloc.stop()
    sys.exit(str(error))

execution_time = time.perf_counter() - start_time
current_memory, peak_memory = tracemalloc.get_traced_memory()
tracemalloc.stop()

print("States explored:", maze.num_explored)
print("Solution cost:", maze.solution_cost)
print("Solution depth:", len(maze.solution[0]))

if algorithm in ("dls", "ids"):
    print("Depth limit used:", maze.depth_limit_used)

print(f"Execution time: {execution_time:.6f} seconds")
print(f"Peak memory: {peak_memory / 1024:.2f} KB")
print("Solution:")
maze.print()

image_filename = f"maze_{algorithm}.png"
maze.output_image(image_filename, show_explored=True)
print("Image created:", image_filename)
