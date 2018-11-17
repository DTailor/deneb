"""Helper tools"""
import datetime
from itertools import zip_longest
from typing import List, Optional

from spotipy import Spotify


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


def clean(iterable):
    """Remove none objects from a list"""
    return [a for a in iterable if a]


def is_present(value: str, items: List[dict], search_by: str) -> dict:
    """
    utility to check if value is present in a list of values from a dict by key
    """
    found = dict()      # type: dict
    for item in items:
        if value == item[search_by]:
            found = item
    return found


def generate_release_date(date: str, precision: str) -> datetime.datetime:
    """Fallback to day precision depending on the offered one"""
    suffix = {
        'year': '-01-01',
        'month': '-01',
        'day': ''
    }
    return datetime.datetime.strptime(
        '{}{}'.format(date, suffix[precision]), '%Y-%m-%d')


def fetch_all(sp: Spotify, data: dict) -> List[Optional[dict]]:
    """iterates till gets all the albums"""
    contents = []   # type: list
    while data:
        contents.extend(data["items"])
        data = sp.client.next(data)                         # noqa: B305
    return contents
