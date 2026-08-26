"""Create the configured PostgreSQL database if it does not exist.

This is a local-development provisioning helper. Production database creation
should remain owned by the deployment platform or a DBA.
"""

import psycopg
from psycopg import sql

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    assert settings.database_url is not None
    with psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        dbname="postgres",
        autocommit=True,
    ) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,)
        ).fetchone()
        if exists:
            print(f"Database already exists: {settings.db_name}")
            return
        connection.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(settings.db_name)))
        print(f"Database created: {settings.db_name}")


if __name__ == "__main__":
    main()
