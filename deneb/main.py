"""Entry point to deneb spotify watcher"""
from db import get_or_create_user
from sp import get_sp_client
from user_update import fetch_user_followed_artists


def main(username, fb_id):
    sp_client, token = get_sp_client(username)
    user = get_or_create_user(fb_id)
    # user.update_market(sp_client.current_user())
    fetch_user_followed_artists(user, sp_client)


main('dann.croitoru', 'dann.croitoru1111')
