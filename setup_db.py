"""
Module 1: PostgreSQL Database Schema Setup
Run this ONCE to create the database tables.

Usage:
  1. Install psycopg2:   pip install psycopg2-binary
  2. Set your DB URL:    export DATABASE_URL=postgresql://user:pass@localhost:5432/ecopackai
  3. Run:                python setup_db.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/ecopackai')

SCHEMA = """
-- Materials table
CREATE TABLE IF NOT EXISTS materials (
    id                    SERIAL PRIMARY KEY,
    material_type         VARCHAR(50)  NOT NULL,
    biodegradability_score INTEGER     DEFAULT 0,
    strength_score         INTEGER     DEFAULT 0,
    avg_co2_emission       FLOAT       DEFAULT 0,
    avg_cost_per_unit      FLOAT       DEFAULT 0,
    recyclable             BOOLEAN     DEFAULT TRUE,
    created_at             TIMESTAMP   DEFAULT NOW()
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id               SERIAL PRIMARY KEY,
    product_id       VARCHAR(20)  UNIQUE NOT NULL,
    material_type    VARCHAR(50)  NOT NULL,
    product_weight_g INTEGER      NOT NULL,
    fragility        VARCHAR(20)  NOT NULL,
    recyclable       VARCHAR(5)   NOT NULL,
    transport_mode   VARCHAR(20)  NOT NULL,
    lca_emission     FLOAT        NOT NULL,
    product_category VARCHAR(50),
    cost_per_unit    FLOAT,
    packaging_option VARCHAR(50),
    co2_impact_index FLOAT,
    cost_eff_index   FLOAT,
    suitability_score FLOAT,
    created_at       TIMESTAMP    DEFAULT NOW()
);

-- Recommendations log
CREATE TABLE IF NOT EXISTS recommendation_log (
    id                 SERIAL PRIMARY KEY,
    product_weight_g   INTEGER,
    material_type      VARCHAR(50),
    fragility          VARCHAR(20),
    recyclable         VARCHAR(5),
    transport_mode     VARCHAR(20),
    product_category   VARCHAR(50),
    top_recommendation VARCHAR(50),
    confidence         FLOAT,
    predicted_cost     FLOAT,
    predicted_co2      FLOAT,
    suitability_score  FLOAT,
    created_at         TIMESTAMP   DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_material   ON products(material_type);
CREATE INDEX IF NOT EXISTS idx_products_category   ON products(product_category);
CREATE INDEX IF NOT EXISTS idx_rec_log_created     ON recommendation_log(created_at);
"""


def setup():
    print(f"Connecting to: {DATABASE_URL[:40]}...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute(SCHEMA)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database schema created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure PostgreSQL is running and DATABASE_URL is correct.")


if __name__ == '__main__':
    setup()
