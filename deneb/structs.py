from collections import namedtuple
from typing import Dict, List, Optional

SpotifyKeys = namedtuple("SpotifyKeys", ["client_id", "client_secret", "client_uri"])
FBAlert = namedtuple("FBAlert", ["key", "url", "notify"])


class AlbumTracks:
    def __init__(self, parent: Dict, tracks: Optional[List[Dict]] = None):
        self.parent = parent
        self.tracks = tracks or []

    def __repr__(self):
        return f"{[a['name'] for a in self.parent['artists']]} - {self.parent['name']}"
