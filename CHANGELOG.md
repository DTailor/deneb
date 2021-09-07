# Changelog

## v2.2.9 (07 sept 2021)

- build docker image remotely (apple m1 vs digitalocean droplet)
- use env vars for dynamic docker images
- update pip

## v2.2.8 (05 september 2021)

- retry policy for jobs
- swtich to python 3.9
- package update
- rm dependabot

## v2.2.7 (17 august 2020)

- don't raise an error if empty albums return (the internal mechanism to discard old albums)
- package update

## v2.2.6 (13 august 2020)

- skip process album if return `None`
- switch to python 3.8.5
- package update

## v2.2.5 (30 june 2020)

- fix sentry errors when `extends()` called on list with a `dict`, but is `None`
- switch CI on python3.8
- package update

## v2.2.4 (28 may 2020)

- all services must (done) use login creds for rabbitmq (fix)

## v2.2.3 (26 may 2020)

- flower use login creds for rabbitmq (fix)

## v2.2.2 (26 may 2020)

- login user/pass for rabbitmq
- pip updates

## v2.2.1 (6 may 2020)

- login user/pass for flower gui
- send message on insuficient scope for spotify on liked yearly

## v2.2.0 (5 may 2020)

- run via docker-compose
- includes: celery, flower, rabbitmq
- hourly task of weekly liked and yearly like separated
- update deploy process
- minor fixes for docker compatibility

## v2.1.1 (30 april 2020)

- switch back to python3.7
- broader exception handling

## v2.1.0 (29 april 2020)

- switch to python3.8
- filter artist albums by date as well

## v2.0.4 (26 april 2020)

- fix circleci build
- new session on every request, no more reuse
- fix `fetch_album` logic

## v2.0.3 (23 april 2020)

- remove faulty log entry
- update readme deploy steps

## v2.0.2 (23 april 2020)

- fix spotipy `max_retries` property rename

## v2.0.1 (23 april 2020)

- fix env variables load for migrations

## v2.0.0 (23 april 2020)

- moved project to github
- Add `Docker` container integration
- Per app configs for every user (user app configs)
- New command `update-playlists-yearly-liked`
- `Makefile` now has `git-tag`, `deploy-test` and `full-deploy`
- `Artist.synced_at` field (last albums fetched timestamp)
- Packages updates
- Major refactors on functionality toolset. Moved method into more consistent modules.

## v1.1.6 (16 march 2020)

New facebook policy imposes `"tag": "ACCOUNT_UPDATE"` to be used when sending messages now.

## v1.1.5 (15 september 2019)

Start work on separate branch for a minanor refactor to enable adding more types
of "workers" (weekly new tracks from artists, and the new one for liked songs from a certain years which can be ran at the same time point).

- Generate name based on last day of the week.

## v1.1.4 (13 september 2019)

Fucks up on `v1.1.3` with updating the artist timestamp (updated_at); somehow by using `filter` with `update` caused updating `None` objects. Fallbacked to `.updated_at=` and `.save()`.

- Change `artist.updated_at` update way.
- Capture exceptions instead of messaged for `sentry`
- Add `migrate` cmd to `Makefile` to run remote migrations

## v1.1.3 (12 september 2019)

- Add timestamps (created_at, updated_at) for "user"
- Always insert on top of playlist (makes it harder reach fresh stuff by scrolls)

## v1.1.2 (25 august 2019)

- Handle first coming users (not having market made deneb skip their check)
- Use `41` as default popularity for tracks if missing
- Add sentry-tag via Makefile
- Migrations doc update
- Timestamps for user table
- Pip update

## v1.1.1

- Dropped calver for semver (feels awkward)
- Removed discarded albums log entry
- Update pip modules
- Now deploy with `make VERSION=version deploy`
- Fix models `updated_at` and `created_at` params (use `auto_now_add`)
