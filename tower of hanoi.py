def hanoi_solver(n):
    rods = [list(range(n, 0, -1)), [], []]
    states = []

    # Record the initial state
    states.append(f"{rods[0]} {rods[1]} {rods[2]}")

    def move(disks, source, auxiliary, target):
        if disks == 1:
            disk = rods[source].pop()
            rods[target].append(disk)
            states.append(f"{rods[0]} {rods[1]} {rods[2]}")
        else:
            move(disks - 1, source, target, auxiliary)
            move(1, source, auxiliary, target)
            move(disks - 1, auxiliary, source, target)

    if n > 0:
        move(n, 0, 1, 2)

    return "\n".join(states)