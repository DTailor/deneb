from collections import namedtuple
from typing import List, Optional
import random


SpotifyKeys = namedtuple(
    "SpotifyKeys", ["client_id", "client_secret", "client_uri"]
)
FBAltert = namedtuple(
    "FBAltert", ["key", "url", "notify"]
)


class SpotifyStats:
    def __init__(self, fb_id: str, playlist: dict, added_items: Optional[List[str]]):
        if added_items is None:
            added_items = []
        self.fb_id = fb_id
        self.playlist = playlist
        self.added_items = added_items

    def describe(self) -> str:
        didnt_add_responses = [
            "Uhh, sorry, no releases today for you.",
            "Didn't find anything new today",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]
        if self.added_items:
            track_noun = "track" if len(self.added_items) == 1 else "tracks"
            return f"I added {len(self.added_items)} {track_noun} to {self.playlist['name']}"
        return random.choice(didnt_add_responses)
