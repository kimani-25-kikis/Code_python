def dfs_n_queens(n):
    if n < 1:
        return []

    solutions = []
    stack = [(0, [])]  # (current_row, queen_positions)

    while stack:
        row, positions = stack.pop()

        if row == n:
            solutions.append(positions)
            continue

        # Push in reverse order so DFS explores columns
        # from left to right.
        for col in range(n - 1, -1, -1):
            valid = True

            for r, c in enumerate(positions):
                if c == col or abs(c - col) == abs(r - row):
                    valid = False
                    break

            if valid:
                stack.append((row + 1, positions + [col]))

    return solutions