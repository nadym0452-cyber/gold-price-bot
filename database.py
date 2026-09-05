import sqlite3
import os
from datetime import datetime
from github_sync import download_db, upload_db

DB_PATH = os.path.join(os.path.dirname(__file__), "shops.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_PATH):
        download_db(DB_PATH)

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


def _names_similar(name1, name2):
    n1 = name1.strip().lower().replace(" ", "")
    n2 = name2.strip().lower().replace(" ", "")
    if n1 == n2:
        return True
    shorter, longer = (n1, n2) if len(n1) <= len(n2) else (n2, n1)
    return len(shorter) >= 4 and shorter in longer


def find_possible_duplicate(shop_name, governorate, phone):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM shops WHERE governorate = ?
    """, (governorate,)).fetchall()
    conn.close()

    for row in rows:
        if phone and row["phone"] and phone.strip() == row["phone"].strip():
            return row
        if _names_similar(shop_name, row["shop_name"]):
            return row
    return None


def add_shop(shop_name, governorate, city, address="", phone="", whatsapp="",
             maps_url="", source_url="", status="Needs Review", notes=""):
    duplicate = find_possible_duplicate(shop_name, governorate, phone)
    if duplicate:
        status = "Possible Duplicate"
        notes = f"{notes} | تكرار محتمل مع محل ID {duplicate['id']}: {duplicate['shop_name']}".strip(" |")

    conn = get_connection()
    conn.execute("""
        INSERT INTO shops (shop_name, governorate, city, address, phone,
                            whatsapp, maps_url, source_url, status, last_updated, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shop_name, governorate, city, address, phone, whatsapp,
          maps_url, source_url, status, datetime.now().strftime("%Y-%m-%d"), notes))
    conn.commit()
    conn.close()
    upload_db(DB_PATH)


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


def get_shops_paginated(governorate, city, page=0, verified_only=True):
    SHOPS_PER_PAGE = 5
    conn = get_connection()
    query = "SELECT * FROM shops WHERE governorate = ? AND city = ?"
    params = [governorate, city]
    if verified_only:
        query += " AND status = 'Verified'"
    query += " ORDER BY shop_name"
    all_rows = conn.execute(query, params).fetchall()
    conn.close()

    start = page * SHOPS_PER_PAGE
    end = start + SHOPS_PER_PAGE
    total_pages = max(1, (len(all_rows) + SHOPS_PER_PAGE - 1) // SHOPS_PER_PAGE)
    return all_rows[start:end], total_pages


def search_shops_paginated(keyword, page=0):
    SHOPS_PER_PAGE = 5
    conn = get_connection()
    pattern = f"%{keyword.strip()}%"
    all_rows = conn.execute("""
        SELECT * FROM shops
        WHERE status = 'Verified'
        AND (shop_name LIKE ? OR city LIKE ? OR governorate LIKE ?)
        ORDER BY shop_name
    """, (pattern, pattern, pattern)).fetchall()
    conn.close()

    start = page * SHOPS_PER_PAGE
    end = start + SHOPS_PER_PAGE
    total_pages = max(1, (len(all_rows) + SHOPS_PER_PAGE - 1) // SHOPS_PER_PAGE)
    return all_rows[start:end], total_pages


def get_shop_by_id(shop_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM shops WHERE id = ?", (shop_id,)).fetchone()
    conn.close()
    return row


def get_pending_shops(limit=1):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM shops WHERE status IN ('Needs Review', 'Possible Duplicate')
        ORDER BY id LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def count_pending_shops():
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM shops WHERE status IN ('Needs Review', 'Possible Duplicate')"
    ).fetchone()[0]
    conn.close()
    return count


def update_shop_status(shop_id, status):
    conn = get_connection()
    conn.execute("UPDATE shops SET status = ? WHERE id = ?", (status, shop_id))
    conn.commit()
    conn.close()
    upload_db(DB_PATH)
