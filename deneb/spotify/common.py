import datetime
from asyncio import sleep
from typing import Any, Dict, Iterable, List, Optional, Tuple  # noqa

import pytz
import sentry_sdk

from deneb.db import Market, User
from deneb.logger import get_logger
from deneb.sp import Spotter
from deneb.structs import SpotifyKeys
from deneb.tools import clean, grouper

_LOGGER = get_logger(__name__)


def find_markets_in_hours(markets: List[Market], hours: List[int]) -> List[Market]:
    """Will return markets where is active the specified hour"""
    valid_markets = []
    for market in markets:
        country_timezones = pytz.country_timezones[market.name]
        timezone = pytz.timezone(country_timezones[0])
        local_time = datetime.datetime.now().astimezone(timezone)
        if local_time.hour in hours:
            valid_markets.append(market)
    return valid_markets


def _user_task_filter(args: Tuple[SpotifyKeys, User, bool]) -> bool:
    """filter for task runner to check if task should be run"""
    if args[1].spotify_token:
        return True
    _LOGGER.info(f"discard task for {args[1]}; missing spotify_token")
    return False


async def _get_to_update_users(
    username: Optional[str] = None, all_markets: Optional[bool] = False
) -> List[User]:
    """if `--username` option used, fetch that user else fetch all users"""
    args = dict()  # type: Dict[str, Any]
    if username is not None:
        args["username"] = username
    without_market_users = []  # type: List[User]

    if not all_markets:
        markets = await Market.all()
        active_markets = find_markets_in_hours(markets, [0, 12])

        # TODO: use logic OR and get rid of this hack
        without_market_users = await User.filter(market_id__isnull=True)

        if not active_markets:
            # no point in fetching users if no markets are good
            return without_market_users

        args["market_id__in"] = [a.id for a in active_markets]

    users = await User.filter(**args)

    return list(users) + list(without_market_users)


async def fetch_all(sp: Spotter, data: Dict) -> List[Dict]:
    """fetch all items avaialble from spotify from first response"""
    contents = []  # type: List[Dict]

    while True:
        contents.extend(data["items"])
        if not data["next"]:
            break
        data = await sp.client.next(data)  # noqa: B305

    return contents


async def get_tracks(sp: Spotter, playlist: dict) -> List[dict]:
    """return playlist tracks"""
    tracks = await sp.client.user_playlist(
        sp.userdata["id"], playlist["id"], fields="tracks,next"
    )
    return await fetch_all(sp, tracks["tracks"])


async def fetch_user_playlists(sp: Spotter) -> List[Dict]:
    """Return user playlists"""
    playlists = []  # type: List[Dict]
    data = await sp.client.user_playlists(sp.userdata["id"])
    playlists = await fetch_all(sp, data)
    return playlists


async def update_spotify_playlist(
    tracks: Iterable, playlist_uri: str, sp: Spotter, insert_top: bool = False
):
    """Add the ids from track iterable to the playlist, insert_top bool does it
    on top of all the items, for fridays"""

    index = 0
    for album_ids in grouper(100, tracks):
        album_ids = clean(album_ids)
        album_ids = [a["id"] for a in album_ids]
        args = (sp.userdata["id"], playlist_uri, album_ids)

        if insert_top:
            args = args + (index,)  # type: ignore

        try:
            await sp.client.user_playlist_add_tracks(*args)
            index += len(album_ids) - 1
            await sleep(0.2)
        except Exception:
            sentry_sdk.capture_exception()
            _LOGGER.exception(
                f"failed add to playlist {playlist_uri}, ids: '{album_ids}'"
            )
