"""Module to handle user related updates"""

from itertools import zip_longest

from db import Artist
from logger import get_logger
from tools import grouper

_LOGGER = get_logger(__name__)


def fetch_artists(sp):
    """fetch user followed artists"""
    artists = list()
    artists_data = sp.client.current_user_followed_artists(limit=50)

    while True:
        if not artists_data["artists"]["next"]:
            break
        artists.extend(artists_data["artists"]["items"])
        artists_data = sp.client.next(artists_data["artists"])          # noqa:B305

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


def check_follows(sp, artists):
    """check with spotify api if artists are followed"""
    lost_follows = []
    for batch in grouper(50, artists):
        artists_ids = ",".join([a.spotify_id for a in batch if a is not None])
        result = sp.client._get(
            "me/following/contains", type="artist", ids=artists_ids
        )
        for artist, is_followed in zip_longest(batch, result, fillvalue=None):
            if artist is None:
                break
            if not is_followed:
                lost_follows.append(artist)
    return lost_follows


def fetch_user_followed_artists(user, sp):
    """fetch artists followed by user"""
    followed_artists = fetch_artists(sp)
    following_ids = [a.spotify_id for a in user.following]

    # followed_artaists - following_ids = new follows
    new_follows = extract_new_follows_objects(followed_artists, following_ids)
    # convert artists to db objects
    new_follows_db = [Artist.to_object(a) for a in new_follows]

    user.add_follows(new_follows_db)

    # following_ids - followed_artists = lost follows
    lost_follows_db = extract_lost_follows_artists(followed_artists, user.following)
    # add second unfollow verification
    # spotify might not return the artist
    lost_follows_db_clean = check_follows(sp, lost_follows_db)
    user.remove_follows(lost_follows_db_clean)

    return new_follows_db, lost_follows_db
