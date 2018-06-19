"""Entry point to deneb spotify watcher"""
import datetime

from user_update import fetch_user_followed_artists
from db import get_or_create_user
from sp import get_sp_client


def main(username, fb_id):
    sp, token = get_sp_client(username)
    user = get_or_create_user(fb_id)
    user.update_market(sp.current_user())
    fetch_user_followed_artists(user, sp)


main('', '')
