"""Module to handle user related updates"""

from itertools import zip_longest

from deneb.db_async import Artist
from deneb.logger import get_logger
from deneb.tools import grouper

_LOGGER = get_logger(__name__)


async def fetch_artists(sp):
    """fetch user followed artists"""
    artists = []
    # TODO: make async call
    artists_data = sp.client.current_user_followed_artists(limit=50)

    while True:
        artists.extend(artists_data["artists"]["items"])
        if not artists_data["artists"]["next"]:
            break
        # TODO: make async call
        artists_data = sp.client.next(artists_data["artists"])  # noqa:B305

    clean_artists = list({v["id"]: v for v in artists}.values())
    return clean_artists


def extract_new_follows_objects(followed_artists, following_ids):
    """returns artists not present in following_ids"""
    new_follows = [a for a in followed_artists if a["id"] not in following_ids]
    return new_follows


def extract_lost_follows_artists(followed_artists, current_following):
    """returns artists not present in following_ids"""
    current_following_ids = [a["id"] for a in followed_artists]
    db_follows_ids = [a.spotify_id for a in current_following]
    lost_follows_ids = [a for a in db_follows_ids if a not in current_following_ids]
    lost_follows = [a for a in current_following if a.spotify_id in lost_follows_ids]
    return lost_follows


async def check_follows(sp, artists):
    """check with spotify api if artists are followed"""
    lost_follows = []
    for batch in grouper(50, artists):
        artists_ids = ",".join([a.spotify_id for a in batch if a is not None])
        # TODO: make async call
        result = sp.client._get("me/following/contains", type="artist", ids=artists_ids)
        for artist, is_followed in zip_longest(batch, result, fillvalue=None):
            if artist is None:
                break
            if not is_followed:
                lost_follows.append(artist)
    return lost_follows


async def fetch_user_followed_artists(user, sp):
    """fetch artists followed by user"""
    followed_artists = await fetch_artists(sp)
    user_db_artists = await user.artists.filter()
    following_ids = [a.spotify_id for a in user_db_artists]

    # followed_artaists - following_ids = new follows
    new_follows = extract_new_follows_objects(followed_artists, following_ids)
    # convert artists to db objects
    new_follows_db = []
    for artist in new_follows:
        db_artist, _ = await Artist.get_or_create(name=artist["name"], spotify_id=artist["id"])
        new_follows_db.append(db_artist)

    if new_follows_db:
        await user.artists.add(*new_follows_db)

    # following_ids - followed_artists = lost follows
    user_db_artists = await user.artists.filter()
    lost_follows_db = extract_lost_follows_artists(followed_artists, user_db_artists)
    # add second unfollow verification
    # spotify might not return the artist
    lost_follows_db_clean = await check_follows(sp, lost_follows_db)

    if lost_follows_db_clean:
        await user.artists.remove(*lost_follows_db_clean)

    return new_follows_db, lost_follows_db_clean
