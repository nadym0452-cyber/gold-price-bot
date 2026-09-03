import sqlite3
import os

DB_FILE = "shops.db"


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            governorate TEXT NOT NULL,
            city TEXT,
            address TEXT,
            phone TEXT,
            whatsapp TEXT,
            maps_url TEXT,
            source TEXT,
            verified TEXT DEFAULT 'needs_review',
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_shop(shop_name, governorate, city=None, address=None, phone=None,
             whatsapp=None, maps_url=None, source=None, verified="needs_review", notes=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shops (shop_name, governorate, city, address, phone,
                            whatsapp, maps_url, source, verified, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shop_name, governorate, city, address, phone, whatsapp, maps_url, source, verified, notes))
    conn.commit()
    conn.close()


def get_cities_by_governorate(governorate):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT city FROM shops
        WHERE governorate = ? AND verified = 'verified' AND city IS NOT NULL
        ORDER BY city
    """, (governorate,))
    rows = cur.fetchall()
    conn.close()
    return [row["city"] for row in rows]


def get_shops(governorate, city=None):
    conn = get_connection()
    cur = conn.cursor()
    if city:
        cur.execute("""
            SELECT * FROM shops WHERE governorate = ? AND city = ? AND verified = 'verified'
            ORDER BY shop_name
        """, (governorate, city))
    else:
        cur.execute("""
            SELECT * FROM shops WHERE governorate = ? AND verified = 'verified'
            ORDER BY shop_name
        """, (governorate,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_shop_by_id(shop_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
    row = cur.fetchone()
    conn.close()
    return row


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
