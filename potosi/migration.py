from peewee import DecimalField, ProgrammingError
from playhouse.migrate import migrate, PostgresqlMigrator

from potosi.db import database
from potosi.log import get_logger
from potosi.models import Order, Trade

logger = get_logger(__name__)


def run_create_tables():
    with database:
        tables = [Order, Trade]
        to_create = []

        for table_name in tables:
            if not database.table_exists(table_name=table_name):
                to_create.append(table_name)

        if len(to_create) > 0:
            database.create_tables(to_create)


def run_migrators():
    migrator = PostgresqlMigrator(database)
    try:
        migrate(
            migrator.set_search_path("public"),
            migrator.add_column(
                "order",
                "price",
                DecimalField(max_digits=14, decimal_places=8, default=0.0),
            ),
        )
    except ProgrammingError as e:
        logger.error(e)


if __name__ == "__main__":
    logger.info("run create tables")
    run_create_tables()

    logger.info("run migrates")
    run_migrators()

    logger.info("finished")
