# Changelog

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
