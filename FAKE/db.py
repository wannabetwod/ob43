"""Работа с PostgreSQL"""
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG


def get_connection():
    """Возвращает новое подключение к БД."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_all(query, params=None):
    """Возвращает все строки как список словарей."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetch_one(query, params=None):
    """Возвращает одну строку как словарь."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()


def execute(query, params=None):
    """Выполняет INSERT/UPDATE/DELETE. Возвращает число затронутых строк."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount


def execute_returning(query, params=None):
    """Выполняет INSERT с RETURNING id. Возвращает id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            row = cur.fetchone()
            return row[0] if row else None