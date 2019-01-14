import asyncio
import time
from collections import defaultdict

from profiling.tracing import TracingProfiler

# from deneb.db import Artist

# profile your program.

def trace_profile(method):
    def profiled(*args, **kw):
        profiler = TracingProfiler()
        profiler.start()
        result = method(*args, **kw)
        profiler.stop()
        profiler.run_viewer()
        return result
    return profiled


_STATS = None


def reset_stats():
    global _STATS
    _STATS = defaultdict(list)


def save_value(key, value):
    global _STATS
    if _STATS is None:
        _STATS = defaultdict(list)
    _STATS[key].append(value)

import statistics

def print_stats():
    global _STATS

    key_spacing = max(len(a) for a in _STATS.keys())
    call_nr_spacing = max(len(str(len(a))) for a in _STATS.values())

    average_data = {key: (len(val), statistics.median(val)) for key, val in _STATS.items()}

    for key, value in sorted(average_data.items(), key=lambda kv: kv[1][1], reverse=True):
        print(f"{key:{key_spacing}} [{value[0]:{call_nr_spacing}}] {(value[1] / 1000):5.3} s")


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        save_value(method.__name__, (te - ts) * 1000)
        return result

    return timed


@timeit
def iter_artists_sync():

    for artist in Artist.select():
        ab = artist.name
        # Artist.get(Artist.name == artist.name)
    profiler.stop()


@timeit
async def _iter_artits_async(objects, aArtist):
    all_objects = await objects.execute(aArtist.select())
    for artist in all_objects:
        ab = artist.name


def iter_artists_async():
    from deneb.db_async import get_objects
    from deneb.db_async import Artist as aArtist
    objects = get_objects()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_iter_artits_async(objects, aArtist))
    loop.close()


def iter_artists():
    print("-> artists iter")
    iter_artists_sync()
    iter_artists_async()


tests = [iter_artists]


def runner():
    for perf_test in tests:
        perf_test()


if __name__ == "__main__":
    runner()
