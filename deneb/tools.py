"""Helper tools"""
import asyncio
import datetime
from itertools import zip_longest
from typing import Any, Callable, Dict, List, Optional, Tuple


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
    for item in items:
        if value == item[search_by]:
            return True, item
    return False, {}


def convert_to_date(date_item: datetime.datetime) -> datetime.date:
    """Issues with Postgres, only accepts datetime.date instances for DateField"""
    return datetime.date(year=date_item.year, month=date_item.month, day=date_item.day)


def generate_release_date(date: str, precision: str) -> datetime.date:
    """Fallback to day precision depending on the offered one"""
    suffix = {"year": "-01-01", "month": "-01", "day": ""}
    return convert_to_date(
        datetime.datetime.strptime(f"{date}{suffix[precision]}", "%Y-%m-%d")
    )


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
