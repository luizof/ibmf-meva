import os
from urllib.parse import urlparse, unquote
import psycopg2
import config

def connect():
    """Create a new database connection.

    The function first checks for the ``DATABASE_URL`` environment variable. If
    present, it is parsed and used to establish the connection. This allows the
    application to work both when running standalone (using the values from
    ``config.py``) and inside Docker where a connection URL is provided via the
    environment.  The connection client encoding is forced to UTF-8 so the
    database correctly handles special characters such as ``ç`` or ``~``.
    """

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=unquote(parsed.password) if parsed.password else None,
        )
    else:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS,
        )

    # Ensure UTF-8 client encoding so special characters are stored correctly
    conn.set_client_encoding("UTF8")
    return conn
