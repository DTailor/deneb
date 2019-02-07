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

### Important

#### DB works async

but had to do a very ugly hack. Change the contents of this file `lib/python3.7/site-packages/tortoise/backends/asyncpg/client.py` with this:

```python
import logging
from functools import wraps
from typing import List, Optional, SupportsInt  # noqa

import asyncpg
from pypika import PostgreSQLQuery

from tortoise.backends.asyncpg.executor import AsyncpgExecutor
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.base.client import (BaseDBAsyncClient, BaseTransactionWrapper,
                                           ConnectionWrapper)
from tortoise.exceptions import (DBConnectionError, IntegrityError, OperationalError,
                                 TransactionManagementError)
from tortoise.transactions import current_transaction_map


def translate_exceptions(func):
    @wraps(func)
    async def wrapped(self, query, *args):
        try:
            return await func(self, query, *args)
        except asyncpg.exceptions.SyntaxOrAccessError as exc:
            raise OperationalError(exc)
        except asyncpg.exceptions.IntegrityConstraintViolationError as exc:
            raise IntegrityError(exc)
    return wrapped


class AsyncpgDBClient(BaseDBAsyncClient):
    DSN_TEMPLATE = 'postgres://{user}:{password}@{host}:{port}/{database}'
    query_class = PostgreSQLQuery
    executor_class = AsyncpgExecutor
    schema_generator = AsyncpgSchemaGenerator

    def __init__(self, user: str, password: str, database: str, host: str, port: SupportsInt,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type

        self._connection = None  # Type: Optional[asyncpg.Connection]
        self.pool = None
        self._transaction_class = type(
            'TransactionWrapper', (TransactionWrapper, self.__class__), {}
        )

    async def init_pool(self):
        dsn = self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )
        self.pool = await asyncpg.create_pool(dsn=dsn, min_size=19, max_size=20)

    async def create_connection(self, with_db: bool) -> None:
        dsn = self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database if with_db else ''
        )
        try:
            self._connection = await asyncpg.connect(dsn)
            self.log.debug(
                'Created connection %s with params: user=%s database=%s host=%s port=%s',
                self._connection, self.user, self.database, self.host, self.port
            )
        except asyncpg.InvalidCatalogNameError:
            raise DBConnectionError("Can't establish connection to database {}".format(
                self.database
            ))

    async def close(self) -> None:
        if self._connection:  # pragma: nobranch
            await self._connection.close()
            self.log.debug(
                'Closed connection %s with params: user=%s database=%s host=%s port=%s',
                self._connection, self.user, self.database, self.host, self.port
            )
            self._connection = None

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(
            'CREATE DATABASE "{}" OWNER "{}"'.format(self.database, self.user)
        )
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script('DROP DATABASE "{}"'.format(self.database))
        except asyncpg.InvalidCatalogNameError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> ConnectionWrapper:
        return self.pool.acquire

    def _in_transaction(self) -> 'TransactionWrapper':
        return self._transaction_class(self.connection_name, self._connection)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as connection:
            self.log.debug('%s: %s', query, values)
            # TODO: Cache prepared statement
            stmt = await connection.prepare(query)
            return await stmt.fetchval(*values)

    @translate_exceptions
    async def execute_query(self, query: str) -> List[dict]:
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as connection:
            self.log.debug(query)
            return await connection.fetch(query)

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as connection:
            self.log.debug(query)
            await connection.execute(query)


class TransactionWrapper(AsyncpgDBClient, BaseTransactionWrapper):
    def __init__(self, connection_name: str, connection) -> None:
        self._connection = connection
        self.log = logging.getLogger('db_client')
        self._transaction_class = self.__class__
        self._old_context_value = None
        self.connection_name = connection_name
        self.transaction = None

    def acquire_connection(self) -> ConnectionWrapper:
        return self.pool.acquire

    async def start(self):
        self.transaction = self._connection.transaction()
        await self.transaction.start()
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    async def commit(self):
        try:
            await self.transaction.commit()
        except asyncpg.exceptions._base.InterfaceError as exc:
            raise TransactionManagementError(exc)
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def rollback(self):
        try:
            await self.transaction.rollback()
        except asyncpg.exceptions._base.InterfaceError as exc:
            raise TransactionManagementError(exc)
        current_transaction_map[self.connection_name].set(self._old_context_value)
```
