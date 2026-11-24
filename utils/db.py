
"""
EcoPackAI — PostgreSQL Database + User Authentication Utilities
Tables: users, prediction_history
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not configured.")

    # Compatibility with older PostgreSQL URL formats
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )

    return psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor
    )


def init_db():
    """Create authentication and prediction history tables."""

    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS prediction_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id)
                        ON DELETE CASCADE,
                    product_name TEXT,
                    product_weight_g INTEGER,
                    material_type TEXT,
                    fragility TEXT,
                    recyclable TEXT,
                    transport_mode TEXT,
                    product_category TEXT,
                    top_packaging TEXT,
                    confidence REAL,
                    predicted_cost REAL,
                    predicted_co2 REAL,
                    suitability_score REAL,
                    all_recs_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        conn.commit()

    finally:
        conn.close()


# USER HELPERS

def create_user(username, email, password):
    """Create a user and return the generated user ID."""

    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (
                username.strip(),
                email.strip().lower(),
                generate_password_hash(password)
            ))

            user_id = cur.fetchone()["id"]

        conn.commit()
        return user_id

    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE email = %s",
                (email.strip().lower(),)
            )
            return cur.fetchone()

    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE id = %s",
                (int(user_id),)
            )
            return cur.fetchone()

    finally:
        conn.close()


def verify_password(user_row, password):
    return check_password_hash(user_row["password_hash"], password)


# PREDICTION HISTORY HELPERS

def save_prediction(user_id, profile, recs):
    """Save a prediction result for a user."""

    import json

    top = recs[0] if recs else {}
    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO prediction_history
                (
                    user_id, product_name, product_weight_g,
                    material_type, fragility, recyclable,
                    transport_mode, product_category,
                    top_packaging, confidence, predicted_cost,
                    predicted_co2, suitability_score, all_recs_json
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                user_id,
                profile.get("product_name", ""),
                profile.get("product_weight_g"),
                profile.get("material_type"),
                profile.get("fragility"),
                profile.get("recyclable"),
                profile.get("transport_mode"),
                profile.get("product_category"),
                top.get("packaging_option", ""),
                top.get("confidence", 0),
                top.get("predicted_cost_usd", 0),
                top.get("predicted_co2_kg", 0),
                top.get("suitability_score", 0),
                json.dumps(recs)
            ))

        conn.commit()

    finally:
        conn.close()


def get_user_history(user_id, limit=20):
    """Get prediction history, newest first."""

    import json

    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM prediction_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))

            rows = cur.fetchall()

        result = []

        for row in rows:
            d = dict(row)

            try:
                d["all_recs"] = json.loads(
                    d.get("all_recs_json") or "[]"
                )
            except Exception:
                d["all_recs"] = []

            result.append(d)

        return result

    finally:
        conn.close()


def clear_user_history(user_id):
    conn = get_db()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM prediction_history WHERE user_id = %s",
                (user_id,)
            )

        conn.commit()

    finally:
        conn.close()
