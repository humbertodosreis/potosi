from os import path

from peewee import DatabaseProxy, Model, SqliteDatabase

from .config import settings

database_proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy


database = SqliteDatabase(
    path.abspath(path.join(settings.ROOT_PATH, "data", "db", "potosi.db")),
    pragmas={"check_same_thread": False, "journal_mode": "wal", "foreign_keys": 1},
    autoconnect=False,
)

database_proxy.initialize(database)
