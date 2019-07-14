# Spotify user followed artists for new daily releases tracker

## db

- install postgres
- go to `sudo vim /etc/postgresql/x.y/main/pg_hba.conf`
  - `local   all         postgres                          trust`
  - `sudo service postgres restart`
  - `sudo -u postgres psql`
  - `ALTER USER postgres PASSWORD '<password>';`
- `sudo -u postgres createdb deneb`
- `sudo -u postgres psql`
- `CREATE USER voyager with PASSWORD '<password>';`
- `grant ALL ON DATABASE deneb TO voyager ;`

## Set up

- `pipenv --python <path-to-3.7>`
- `make install-dev`
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

- `make deploy` - deploy on server
- `pipenv run fab full-run` - run whole script on server with predefined parameters; see bellow
  - `--notify=False` - don't send any fb messages
  - `--force=False` - dont update artist if not the case

### Sentry Release

#### Assumes you're in a git repository

```bash
sentry-cli releases new -p deneb "2019.07.01"
sentry-cli releases set-commits --auto "2019.07.01"
```

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

## Testing

## Develop

### Database

```bash
docker pull postgres
mkdir -p $HOME/docker/volumes/postgres
docker run --rm   --name pg-docker -e POSTGRES_PASSWORD=$DB_PASSWORD -e POSTGRES_USER=$DB_USER -d -p 5432:5432 -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data  postgres
```

## Local

`make test`

### CI

- [circleci](https://circleci.com/bb/DTailor/deneb)
