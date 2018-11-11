"""Helper tools"""
import datetime
from itertools import zip_longest


def grouper(n, iterable, padvalue=None):                                           # pylint: disable=C0103
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


def clean(iterable):
    """Remove none objects from a list"""
    return [a for a in iterable if a]


def is_present(value: str, artists: [dict], search_by: str) -> bool:
    """
    utility to check if value is present in a list of values from a dict by key
    """
    func = lambda value, artists: bool(value in [a[search_by] for a in artists])  # noqa
    return func(value, artists)


def generate_release_date(date: str, precision: str) -> datetime.datetime:
    """Fallback to day precision depending on the offered one"""
    suffix = {
        'year': '-01-01',
        'month': '-01',
        'day': ''
    }
    return datetime.datetime.strptime(
        '{}{}'.format(date, suffix[precision]), '%Y-%m-%d')
