"""Helper tools"""
import datetime
from collections import Callable, OrderedDict
from itertools import zip_longest
from typing import List

from spotipy import Spotify


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)] * n, fillvalue=padvalue)


def clean(iterable):
    """Remove none objects from a list"""
    return [a for a in iterable if a]


def is_present(value: str, items: List[dict], search_by: str) -> dict:
    """
    utility to check if value is present in a list of values from a dict by key
    """
    found = {}  # type: dict
    for item in items:
        if value == item[search_by]:
            found = item
    return found


def generate_release_date(date: str, precision: str) -> datetime.datetime:
    """Fallback to day precision depending on the offered one"""
    suffix = {"year": "-01-01", "month": "-01", "day": ""}
    return datetime.datetime.strptime(
        "{}{}".format(date, suffix[precision]), "%Y-%m-%d"
    )


def fetch_all(sp: Spotify, data: dict) -> List[dict]:
    """iterates till gets all the albums"""
    contents = []  # type: List[dict]
    while data:
        contents.extend(data["items"])
        data = sp.client.next(data)  # noqa: B305
    return contents


class DefaultOrderedDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    def __init__(self, default_factory=None, *a, **kw):
        if default_factory is not None and not isinstance(default_factory, Callable):
            raise TypeError("first argument must be callable")
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()  # noqa
        else:
            args = (self.default_factory,)
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy

        return type(self)(self.default_factory, copy.deepcopy(self.items()))

    def __repr__(self):
        return "OrderedDefaultDict(%s, %s)" % (
            self.default_factory,
            OrderedDict.__repr__(self),
        )
