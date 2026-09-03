import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "shops.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            governorate TEXT NOT NULL,
            city TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            whatsapp TEXT,
            maps_url TEXT,
            source_url TEXT,
            status TEXT DEFAULT 'Needs Review',
            last_updated TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def count_shops():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
    conn.close()
    return count


def add_shop(shop_name, governorate, city, address="", phone="", whatsapp="",
             maps_url="", source_url="", status="Needs Review", notes=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO shops (shop_name, governorate, city, address, phone,
                            whatsapp, maps_url, source_url, status, last_updated, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shop_name, governorate, city, address, phone, whatsapp,
          maps_url, source_url, status, datetime.now().strftime("%Y-%m-%d"), notes))
    conn.commit()
    conn.close()


def get_cities(governorate, verified_only=True):
    conn = get_connection()
    query = "SELECT DISTINCT city FROM shops WHERE governorate = ?"
    params = [governorate]
    if verified_only:
        query += " AND status = 'Verified'"
    query += " ORDER BY city"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [r["city"] for r in rows]


def get_shops(governorate, city, verified_only=True):
    conn = get_connection()
    query = "SELECT * FROM shops WHERE governorate = ? AND city = ?"
    params = [governorate, city]
    if verified_only:
        query += " AND status = 'Verified'"
    query += " ORDER BY shop_name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_shop_by_id(shop_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()
    conn.close()
    return row
def get_pending_shops(limit=1):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM shops WHERE status = 'Needs Review'
        ORDER BY id LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def count_pending_shops():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM shops WHERE status = 'Needs Review'").fetchone()[0]
    conn.close()
    return count


def update_shop_status(shop_id, status):
    conn = get_connection()
    conn.execute("UPDATE shops SET status = ? WHERE id = ?", (status, shop_id))
    conn.commit()
    conn.close()
