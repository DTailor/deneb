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

## Docker

This project is containerized.

### Purge everything

```bash
docker rm $(docker ps --filter=status=exited --filter=status=created -q)
docker rmi $(docker images -a --filter=dangling=true -q)
docker rmi $(docker images -a -q)
```

### Build image

```bash
docker build -t deneb .
```

### Enter it

```bash
docker run -i deneb /bin/sh
```

### Run it

```bash
docker run --network host  --env-file .env deneb pipenv run python -m deneb full-run --user <username> --notify --all-markets
docker run --network host  --env-file .env deneb pipenv run python -m deneb update-playlists-yearly-liked --user <username> --notify
```

## Deploy

- Update poetry packages if the case
- `Make test`
- Add `CHANGELOG` entry with version deployed & changelog
- Update `deneb/config.py` app version
- Update `pyproject.toml` app version
- Update `.env` app version (production also)
<!-- Commit -->
- `git tag -a <version> -m "release <version>"`
- `git push --tags`
- `make migrate`
- `make VERSION=<version> sentry`
- `make VERSION=<version> deploy`

or for the last 7 steps

``make VERSION=<version> full-deploy``

### Update config.py version

- Change version in code
- Commit change with message `bump to {version}`

### Create git tag

- `git tag -a {version} -m "release {version}"`
- `git push --tags`

### Release code

- `make VERSION={version} deploy` - deploy on server
- `pipenv run fab full-run` - run whole script on server with predefined parameters; see bellow
  - `--notify=False` - don't send any fb messages
  - `--force=False` - dont update artist if not the case

### Sentry Release

#### Assumes you're in a git repository

```bash
make VERSION=version sentry
```

## Cli tool

There's a cli tool available to use the tool easier.

### Commands

- `pipenv run python -m deneb`
  - `full-run` (runs all commands bellow)
    - `--force` - ignore artist synced_at timestamp (for: `update-followed`)
    - `--notify` - send fb users what tracks were added to playlist
    - `--dry-run` - dont'a add tracks to spotify playlist (for: all)
    - `--user <spotify_id>` - full run for specific spotify id (for: all)
    - `--all-markets` - will query all markets instead of 12/24 hour ones (for: `update-followed`, `update-playlists`)
    - `--year <year>` - collect liked tracks from specific year (for: `update-playlists-yearly-liked`)
  - `update-followed` (collect user followed artists and albums (from current year) from spotify )
    - `--force` - ignore artist synced_at timestamp
    - `--user <spotify_id>` - full run for specific spotify id
    - `--all-markets` - will query all markets instead of 12/24 hour ones
  - `update-playlists`(update current week realeased tracks playlist from followed artists)
    - `--notify` - send fb users what tracks were added to playlist
    - `--dry-run` - dont'a add tracks to spotify playlist
    - `--user <spotify_id>` - full run for specific spotify id
    - `--all-markets` - will query all markets instead of 12/24 hour ones
  - `update-playlists-yearly-liked` (update liked songs from released specific year playlist)
    - `--notify` - send fb users what tracks were added to playlist
    - `--dry-run` - dont'a add tracks to spotify playlist
    - `--user <spotify_id>` - full run for specific spotify id
    - `--year <year>` - collect liked tracks from specific year

## Testing

## Develop

### Database

```bash
docker pull postgres
mkdir -p $HOME/docker/volumes/postgres
docker run --rm   --name pg-docker -e POSTGRES_PASSWORD=$DB_PASSWORD -e POSTGRES_USER=$DB_USER -d -p 5432:5432 -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data  postgres
```

#### Migrations

Are done by using alembic:

- `pipenv run alembic upgrade head` - migrate to last state
- `pipenv run alembic revision -m "Revision Message"` - create a new db revision
- `pipenv run alembic downgrade base` - destroy all (AHTUNG!)

## Local

`make test`

### CI

- [circleci](https://circleci.com/gh/DTailor/deneb)
