"""Shared helpers for migration scripts."""
from alembic import op


def run_sql(sql: str) -> None:
    """Run a script of several statements. psycopg only allows this with no bound parameters."""
    with op.get_bind().connection.cursor() as cursor:
        cursor.execute(sql)
