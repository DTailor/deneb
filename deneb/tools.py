"""Helper tools"""
import asyncio
import datetime
from itertools import zip_longest
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytz
from spotipy import Spotify

from deneb import db  # noqa


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return zip_longest(*[iter(iterable)] * n, fillvalue=padvalue)


def clean(iterable):
    """Remove none objects from a list"""
    return [a for a in iterable if a]


def search_dict_by_key(
    value: str, items: List[dict], search_by: str
) -> Tuple[bool, Dict]:
    """
    utility to check if value is present in a list of values from a dict by key
    """
    found = {}  # type: dict
    is_found = False
    for item in items:
        if value == item[search_by]:
            is_found = True
            found = item
    return is_found, found


def convert_to_date(date_item: datetime.datetime) -> datetime.date:
    """Issues with Postgres, only accepts datetime.date instances for DateField"""
    return datetime.date(year=date_item.year, month=date_item.month, day=date_item.day)


def generate_release_date(date: str, precision: str) -> datetime.date:
    """Fallback to day precision depending on the offered one"""
    suffix = {"year": "-01-01", "month": "-01", "day": ""}
    return convert_to_date(
        datetime.datetime.strptime(f"{date}{suffix[precision]}", "%Y-%m-%d")
    )


def should_fetch_more_albums(
    albums: List[Dict], to_check_album_types: List[str]
) -> Tuple[bool, List[Dict], List[str]]:
    required_year = str(datetime.datetime.now().year)
    validated_albums = []  # type: List[dict]
    for album in albums:
        if album["album_type"] in to_check_album_types:
            to_check_album_types.remove(album["album_type"])

        if required_year in album["release_date"]:
            validated_albums.append(album)
        else:
            if not to_check_album_types:
                return False, validated_albums, to_check_album_types

    return True, validated_albums, to_check_album_types


async def fetch_all_albums(sp: Spotify, data: dict) -> List[Dict]:
    # ok, so this new `to_check_album_types` is a hack to fix-up a problem
    # the issues constits in the fact the as we fetch albums
    # we retrieve several `album_types`, like `album`, `single`, `appears_on`
    # and they are returned back in descendant order by `release_date`, the catch
    # is that they are group, meaning that you'll then them ordered that way but
    # first the `albums`, then the `single` and `appears_on`. This made the script
    # to miss some `sinlge` and `appears_on` type of albums

    to_check_album_types = ["album", "single", "appears_on"]
    contents = []

    while True:
        should, albums, to_check_album_types = should_fetch_more_albums(
            data["items"], to_check_album_types
        )
        contents.extend(albums)
        if not should or not data["next"]:
            break
        data = await sp.client.next(data)  # noqa: B305

    # there are some duplicates, remove them
    contents = list({v["id"]: v for v in contents}.values())
    return contents


async def fetch_all(sp: Spotify, data: dict) -> List[Dict]:
    """iterates till gets all the items"""
    contents = []  # type: List[dict]

    while True:
        contents.extend(data["items"])
        if not data["next"]:
            break
        data = await sp.client.next(data)  # noqa: B305

    return contents


def _create_jobs(func: Callable, args_items: List[Any]) -> List[asyncio.Future]:
    return [asyncio.ensure_future(func(*item)) for item in args_items]


def _take(
    amount: int, items: List[Any], can_add_filter: Callable
) -> Tuple[List[Any], List[Any]]:
    taken_items = []  # type: List[Any]
    for idx, item in enumerate(items):
        if len(taken_items) == amount:
            return taken_items, items[idx:]
        if can_add_filter(args=item):
            taken_items.append(item)
    return taken_items, []


async def run_tasks(
    queue_size: int,
    args_items_left: List[Any],
    afunc: Callable,
    items_filter: Optional[Callable] = None,
) -> List[Any]:
    items_filter = items_filter or (lambda args: args)

    args_items_batch, args_items_left = _take(queue_size, args_items_left, items_filter)
    jobs = _create_jobs(afunc, args_items_batch)
    job_results = []

    while jobs:
        done_tasks, pending = await asyncio.wait(
            jobs, return_when=asyncio.FIRST_COMPLETED
        )
        while done_tasks:
            done_task = done_tasks.pop()
            jobs.remove(done_task)
            result = await done_task
            job_results.append(result)

        if args_items_left:
            required_amount = queue_size - len(pending)
            args_items_batch, args_items_left = _take(
                required_amount, args_items_left, items_filter
            )
            jobs.extend(_create_jobs(afunc, args_items_batch))

    return job_results


def find_markets_in_hours(
    markets: List["db.Market"], hours: List[int]
) -> List["db.Market"]:
    """Will return markets where is active the specified hour"""
    valid_markets = []
    for market in markets:
        country_timezones = pytz.country_timezones[market.name]
        timezone = pytz.timezone(country_timezones[0])
        local_time = datetime.datetime.now().astimezone(timezone)
        if local_time.hour in hours:
            valid_markets.append(market)
    return valid_markets
