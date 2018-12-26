import random
from collections import namedtuple
from typing import Dict, List, Optional


SpotifyKeys = namedtuple("SpotifyKeys", ["client_id", "client_secret", "client_uri"])
FBAlert = namedtuple("FBAlert", ["key", "url", "notify"])


class AlbumTracks:
    def __init__(
        self, parent: Optional[Dict] = None, tracks: Optional[List[Dict]] = None
    ):
        self.parent = parent
        self.tracks = tracks or []


class SpotifyStats:
    def __init__(self, fb_id: str, playlist: dict, added_items: Dict[str, List]):
        self.fb_id = fb_id
        self.playlist = playlist
        self.added_albums = added_items["albums"]
        self.added_tracks = added_items["tracks"]

    @staticmethod
    def humanize_track(album: AlbumTracks) -> str:
        track = album.tracks[0]
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"{artists} - {track['name']}"

    def describe(self) -> str:
        didnt_add_responses = [
            "Uhh, sorry, no releases today for you.",
            "Didn't find anything new today",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]
        if self.added_albums or self.added_tracks:
            return_msg = f"{self.playlist['name']}\n"

            if self.added_albums:
                return_msg = f"{return_msg}Albums:\n"
                for album in self.added_albums:
                    featuring_artists = ", ".join(a.name for a in album.parent.artists())
                    tmp_msg = f"- [{featuring_artists} - {album.parent.name}]\n"
                    for track in album.tracks:
                        tmp_msg = f"{tmp_msg}   * {track['name']}\n"
                    return_msg = f"{return_msg}{tmp_msg}\n"

            if self.added_tracks:
                return_msg = f"{return_msg}Tracks:\n"
                for track in self.added_tracks:
                    return_msg = f"{return_msg} * {self.humanize_track(track)}\n"

                return return_msg

        return random.choice(didnt_add_responses)
