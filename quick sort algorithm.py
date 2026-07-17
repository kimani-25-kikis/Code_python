def quick_sort(numbers):
    # Base case
    if len(numbers) <= 1:
        return numbers[:]

    # Choose the last element as the pivot
    pivot = numbers[-1]

    # Partition the list
    less = []
    equal = []
    greater = []

    for num in numbers:
        if num < pivot:
            less.append(num)
        elif num > pivot:
            greater.append(num)
        else:
            equal.append(num)

    
    return quick_sort(less) + equal + quick_sort(greater)