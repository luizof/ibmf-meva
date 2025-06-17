# config.py
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "BD_MEP")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "banco@mep")
SENSOR_PORT = int(os.getenv("SENSOR_PORT", "8899"))
