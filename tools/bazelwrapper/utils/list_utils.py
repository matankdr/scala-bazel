def split_after(iterable, pred):
    # taken from more_iterutils
    """Yield lists of items from *iterable*, where each list ends with an
    item where callable *pred* returns ``True``:

        >>> list(split_after('one1two2', lambda s: s.isdigit()))
        [['o', 'n', 'e', '1'], ['t', 'w', 'o', '2']]

        >>> list(split_after(range(10), lambda n: n % 3 == 0))
        [[0], [1, 2, 3], [4, 5, 6], [7, 8, 9]]

    """
    buf = []
    for item in iterable:
        buf.append(item)
        if pred(item) and buf:
            yield buf
            buf = []
    if buf:
        yield buf