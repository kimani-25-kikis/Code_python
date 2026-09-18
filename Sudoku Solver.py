def solve(board):
    empty = find_empty(board)
    if not empty:
        return True
    r, c = empty
    for n in range(1, 10):
        if valid(board, r, c, n):
            board[r][c] = n
            if solve(board):
                return True
            board[r][c] = 0
    return False

def find_empty(board):
    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                return (i, j)
    return None

def valid(board, r, c, n):
    if n in board[r]:
        return False
    if any(board[i][c] == n for i in range(9)):
        return False
    br, bc = 3 * (r // 3), 3 * (c // 3)
    for i in range(br, br + 3):
        for j in range(bc, bc + 3):
            if board[i][j] == n:
                return False
    return True

def print_board(b):
    for i, row in enumerate(b):
        if i % 3 == 0 and i != 0:
            print("-" * 21)
        print(" ".join(str(x) if x else "." for x in row[:3]) + " | " +
              " ".join(str(x) if x else "." for x in row[3:6]) + " | " +
              " ".join(str(x) if x else "." for x in row[6:]))

if __name__ == "__main__":
    puzzle = [
        [5,3,0,0,7,0,0,0,0],
        [6,0,0,1,9,5,0,0,0],
        [0,9,8,0,0,0,0,6,0],
        [8,0,0,0,6,0,0,0,3],
        [4,0,0,8,0,3,0,0,1],
        [7,0,0,0,2,0,0,0,6],
        [0,6,0,0,0,0,2,8,0],
        [0,0,0,4,1,9,0,0,5],
        [0,0,0,0,8,0,0,7,9],
    ]
    if solve(puzzle):
        print_board(puzzle)
    else:
        print("No solution")