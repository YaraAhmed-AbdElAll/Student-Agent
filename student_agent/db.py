import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_PORT"]


def get_connection():
    """Open and return a new connection to the database."""
    missing = [name for name in REQUIRED_VARS if os.getenv(name) is None]
    if missing:
        raise RuntimeError(f"Missing in .env: {', '.join(missing)}")

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )