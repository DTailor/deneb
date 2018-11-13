Spotify user followed artists for new daily releases tracker

### db

 - `createdb deneb`
 - `psql`
 - `create database deneb`
 - `CREATE USER voyager with PASSWORD "<password>";`
 - `grant ALL ON DATABASE deneb TO voyager ;`


### Set up
 - `mkvirtualenv danube --python=python3`
 - `pip install -r requirements.txt`
 - `cp scripts/spotify_keys_sample.sh scripts/spotify_keys.sh`
 - fill in data for `scripts/spotify_keys.sh`
 - `source scripts/spotify_keys.sh`
