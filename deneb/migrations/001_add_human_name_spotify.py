import os

from playhouse.migrate import PostgresqlDatabase, PostgresqlMigrator, CharField, migrate

my_db = PostgresqlDatabase(
    os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
)
migrator = PostgresqlMigrator(my_db)

migrate(
    migrator.add_column('user', 'display_name', CharField(default='')),
)
