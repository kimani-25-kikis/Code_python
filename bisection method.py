def square_root_bisection(square_target, tolerance=1e-7, maximum_iterations=100):
    if square_target < 0:
        raise ValueError(
            "Square root of negative number is not defined in real numbers"
        )

    if square_target == 0 or square_target == 1:
        print(f"The square root of {square_target} is {square_target}")
        return square_target

    low = 0
    high = max(1, square_target)

    for _ in range(maximum_iterations):
        mid = (low + high) / 2

        if high - low <= tolerance:
            print(f"The square root of {square_target} is approximately {mid}")
            return mid

        if mid * mid < square_target:
            low = mid
        else:
            high = mid

    print(f"Failed to converge within {maximum_iterations} iterations")
    return None