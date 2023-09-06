def arr_chunk_groups(arr: list, size: int):
    res = []
    for i in range(0, len(arr), size):
        res.append(arr[i:i + size])
    return res
