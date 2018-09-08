"""Module to handle artist updates"""


def update_artist_albums(artist):
    """Fetch and mirror locally artist albums"""
    albums = fetch_albums(artist)
    spotify_and_db = []
    for detailed_albums in detailify_albums(albums):
        for album in detailed_albums:
            spotify_and_db.append(
                (album, init_contribs(album, artist))
            )

    for spotify_album, db_contribs in spotify_and_db:
        for db_contrib in db_contribs:
            update_album_marketplace(
                db_contrib, spotify_album['available_markets'])
    q = (
        Artist
        .update(timestamp=datetime.datetime.now())
        .where(Artist.id == artist.id)
    )
    q.execute()
    return spotify_and_db
