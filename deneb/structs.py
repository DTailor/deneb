from collections import namedtuple
from typing import Dict, List, Optional, Union

from deneb.db import Album

SpotifyKeys = namedtuple("SpotifyKeys", ["client_id", "client_secret", "client_uri"])
FBAlert = namedtuple("FBAlert", ["key", "url", "notify"])


class AlbumTracks:
    def __init__(
        self, parent: Union[Dict, Album], tracks: Optional[List[Dict]] = None
    ):
        self.parent = parent
        self.tracks = tracks or []
