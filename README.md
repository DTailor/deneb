# Spotify user followed artists for new daily releases tracker

## db

- `createdb deneb`
- `psql`
- `create database deneb;`
- `CREATE USER voyager with PASSWORD '<password>';`
- `grant ALL ON DATABASE deneb TO voyager ;`

## Set up

- `pipenv --python <path-to-3.7>`
- `pipenv install`
- `cp .env_example .env`
- fill in data for `.env`
  - `spotify`
    - `SPOTIPY_CLIENT_ID`
    - `SPOTIPY_CLIENT_SECRET`
    - `SPOTIPY_REDIRECT_URI`
    - `SPOTIPY_SCOPE`
  - `db data`
    - `DB_NAME`
    - `DB_USER`
    - `DB_PASSWORD`
    - `DB_HOST`
  - `deployment`
    - `SSH_USER`
    - `SSH_HOST`
  - `fb notify`
    - `FB_API_URL`
    - `FB_API_KEY`
  - `sentry logging`
    - `SENTRY_URL`

## Deploy

- `pipenv run fab deploy` - deploy on server
- `pipenv run fab full-run` - run on server
  - `--notify=False` - don't send any fb messages
  - `--force=False` - dont update artist if not the case

## Cli tool

There's a cli tool available to use the tool easier.

### Commands

- `pipenv run python -m deneb`
  - `full-run`
    - `--force` - validate to check artist anyway
    - `--notify` - send fb users what tracks were added to playlist
    - `--dry-run` - dont'a add tracks to spotify playlist
    - `--user <spotify_id>` - full run for specific spotify id
  - `update-followed`
    - `--force` - validate to check artist anyway
    - `--user <spotify_id>` - full run for specific spotify id
  - `update-playlists`
    - `--notify` - send fb users what tracks were added to playlist
    - `--dry-run` - dont'a add tracks to spotify playlist
    - `--user <spotify_id>` - full run for specific spotify id
    
