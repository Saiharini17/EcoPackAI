"""
EcoPackAI — SQLite Database + User Authentication Utilities
Tables: users, prediction_history
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ecopackai.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    UNIQUE NOT NULL,
            email        TEXT    UNIQUE NOT NULL,
            password_hash TEXT   NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS prediction_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            product_name     TEXT,
            product_weight_g INTEGER,
            material_type    TEXT,
            fragility        TEXT,
            recyclable       TEXT,
            transport_mode   TEXT,
            product_category TEXT,
            top_packaging    TEXT,
            confidence       REAL,
            predicted_cost   REAL,
            predicted_co2    REAL,
            suitability_score REAL,
            all_recs_json    TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    conn.commit()
    conn.close()


# ── User helpers ─────────────────────────────────────────────────────────────

def create_user(username, email, password):
    """Insert a new user. Returns user id or raises on duplicate."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), generate_password_hash(password))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (int(user_id),)
        ).fetchone()
    finally:
        conn.close()


def verify_password(user_row, password):
    return check_password_hash(user_row['password_hash'], password)


# ── History helpers ───────────────────────────────────────────────────────────

def save_prediction(user_id, profile, recs):
    """Save a prediction result for a user."""
    import json
    top = recs[0] if recs else {}
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO prediction_history
                (user_id, product_name, product_weight_g, material_type, fragility,
                 recyclable, transport_mode, product_category, top_packaging,
                 confidence, predicted_cost, predicted_co2, suitability_score, all_recs_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            user_id,
            profile.get('product_name', ''),
            profile.get('product_weight_g'),
            profile.get('material_type'),
            profile.get('fragility'),
            profile.get('recyclable'),
            profile.get('transport_mode'),
            profile.get('product_category'),
            top.get('packaging_option', ''),
            top.get('confidence', 0),
            top.get('predicted_cost_usd', 0),
            top.get('predicted_co2_kg', 0),
            top.get('suitability_score', 0),
            json.dumps(recs)
        ))
        conn.commit()
    finally:
        conn.close()


def get_user_history(user_id, limit=20):
    """Get prediction history for a user, newest first."""
    import json
    conn = get_db()
    try:
        rows = conn.execute('''
            SELECT * FROM prediction_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d['all_recs'] = json.loads(d.get('all_recs_json') or '[]')
            except Exception:
                d['all_recs'] = []
            result.append(d)
        return result
    finally:
        conn.close()


def clear_user_history(user_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM prediction_history WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
