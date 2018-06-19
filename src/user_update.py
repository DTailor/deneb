"""Module to handle user related updates"""
from db import Artist


def fetch_artists(sp_client):
    artists = list()
    artists_data = sp_client.current_user_followed_artists(limit=50)

    while True:
        if not artists_data['artists']['next']:
            break
        artists.extend(artists_data['artists']['items'])
        artists_data = sp_client.next(artists_data['artists'])

    # TODO: spotify return same artists more times, why?
    # TODO: spotify doesn't return all artists user follows, why?
    clean_artists = list({v['id']:v for v in artists}.values())
    return clean_artists


def extract_new_follows_objects(followed_artists, following_ids):
    new_follows = [a for a in followed_artists if a['id'] not in following_ids]
    return new_follows


def extract_lost_follows_artists(followed_artists, following_ids):
    lost_follows = [a for a in followed_artists if not a['id'] in following_ids]
    return lost_follows


def fetch_user_followed_artists(user, sp):
    """fetch artists followed by user"""
    followed_artists = fetch_artists(sp)
    following_ids = [a.spotify_id for a in user.following]

    # followed_artists - following_ids = new follows
    new_follows = extract_new_follows_objects(followed_artists, following_ids)

    # convert artists to db objects
    new_follows_db = [Artist.to_object(a) for a in new_follows]

    user.add_follows(new_follows_db)
    print('new follows {}: {}'.format(user, len(new_follows_db)))

    # # following_ids - followed_artists = lost follows
    # lost_follows_db = extract_lost_follows_artists(followed_artists, following_ids)

    # add second unfollow verification
    # spotify might not return the artist
    # user.remove_follows(lost_follows_db)
    # print('lost follows {}: {}'.format(user, len(lost_follows_db)))

