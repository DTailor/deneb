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
- `pipenv shell`
- `python src/main.py` to fetch new followers and artist new albums
- `python src/weekler.py` to create spotify playlist with this weeks new stuff

## Improvs

- tests
- sentry
- docker
- celery
- features
  - last 30 days playlist
