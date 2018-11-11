"""Entry point to deneb spotify watcher"""

from artist_update import get_new_releases
from db import get_or_create_user
from logger import get_logger
from sp import get_sp_client
from user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)

def main(username, fb_id):
    _LOGGER.info('')
    _LOGGER.info('------------ RUN ---------------')
    _LOGGER.info('')
    sp_client, token = get_sp_client(username)
    user, created = get_or_create_user(fb_id)
    _LOGGER.info(f"Using {user}; created status is {created}")
    user.update_market(sp_client.current_user())
    _LOGGER.info(f"Updated marketplace for {user}")
    fetch_user_followed_artists(user, sp_client)
    get_new_releases(sp_client)



main('dann.croitoru', 'dann.croitoru1111')
