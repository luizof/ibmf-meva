import psycopg2
import config

def connect():
    conn = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASS,
        options='-c client_encoding=UTF8'
    )
    return conn
