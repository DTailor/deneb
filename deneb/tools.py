from itertools import zip_longest


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


def clean(iterable):
    return [a for a in iterable if a]


def is_present(value: str, artists: [dict], search_by: str):
    """
    utility to check if value is present in a list of values from a dict by key
    """
    func = lambda value, artists: bool(value in [a[search_by] for a in artists])  # noqa
    return func(value, artists)
