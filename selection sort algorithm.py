def selection_sort(items):
    n = len(items)

    for i in range(n - 1):
        # Assume the first unsorted element is the minimum
        min_index = i

        # Find the index of the smallest element
        for j in range(i + 1, n):
            if items[j] < items[min_index]:
                min_index = j

        # Swap only if needed
        if min_index != i:
            items[i], items[min_index] = items[min_index], items[i]

    return items