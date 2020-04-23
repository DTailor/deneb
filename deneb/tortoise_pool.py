from contextlib import asynccontextmanager

import asyncpg
from tortoise import Tortoise
from tortoise.backends.asyncpg.client import AsyncpgDBClient


@asynccontextmanager
async def get_pool(client: "PoolAsyncpgDBClient") -> asyncpg.connection:
    if not client.pool:
        await client.init_pool()
    try:
        async with client.pool.acquire() as connection:
            yield connection
    finally:
        pass


class PoolAsyncpgDBClient(AsyncpgDBClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pool = None

    async def init_pool(self):
        dsn = self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )
        self.pool = await asyncpg.create_pool(dsn=dsn, min_size=19, max_size=20)
        self.con = await self.pool.acquire()
        return self.pool

    async def release_pool(self):
        await self.pool.release(self.con)

    def acquire_connection(self):
        return get_pool(self)


class PoolTortoise(Tortoise):
    @classmethod
    def _discover_client_class(cls, engine):
        return PoolAsyncpgDBClient
