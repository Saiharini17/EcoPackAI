"""
Module 1 & 2: Data Collection, Cleaning & Feature Engineering
Enhances raw dataset with missing columns and derived sustainability features.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'packaging_dataset.csv')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed_dataset.csv')

# ── Cost mapping per packaging option (USD, realistic ranges) ────────────────
COST_MAP = {
    'Recycled Cardboard': (0.30, 0.80),
    'Paper Wrap':         (0.10, 0.40),
    'Bio Bubble Wrap':    (0.50, 1.20),
    'Cornstarch Wrap':    (0.60, 1.50),
    'Mushroom Foam':      (0.80, 2.00),
    'Minimalist Pouch':   (0.20, 0.60),
}

# ── Biodegradability score per material (0–100) ──────────────────────────────
BIO_MAP = {
    'Paper':       95,
    'Bioplastic':  80,
    'Plastic':     10,
    'Metal':        5,
    'Glass':       15,
    'Ceramic':     20,
}

# ── Strength score per packaging option (0–100) ──────────────────────────────
STRENGTH_MAP = {
    'Recycled Cardboard': 65,
    'Paper Wrap':         40,
    'Bio Bubble Wrap':    70,
    'Cornstarch Wrap':    55,
    'Mushroom Foam':      75,
    'Minimalist Pouch':   50,
}

# ── Product category derived from Material_Type + Fragility ──────────────────
def assign_category(row):
    material = row['Material_Type']
    fragility = row['Fragility']
    if material in ['Glass', 'Ceramic']:
        return 'Home & Decor'
    elif material == 'Metal':
        return 'Electronics' if fragility == 'High' else 'Industrial'
    elif material == 'Plastic':
        return 'Cosmetics' if fragility == 'Medium' else 'E-Commerce'
    elif material == 'Paper':
        return 'Food & Beverage'
    elif material == 'Bioplastic':
        return 'Pharma & Health'
    return 'General'


def load_and_enhance(path=DATA_PATH):
    df = pd.read_csv(path)

    # ── Add Cost_per_unit ────────────────────────────────────────────────────
    np.random.seed(42)
    df['Cost_per_unit'] = df['Packaging_Option'].apply(
        lambda p: round(np.random.uniform(*COST_MAP.get(p, (0.20, 1.00))), 2)
    )

    # ── Add Biodegradability_Score ───────────────────────────────────────────
    df['Biodegradability_Score'] = df['Material_Type'].map(BIO_MAP).fillna(30)

    # ── Add Strength_Score ───────────────────────────────────────────────────
    df['Strength_Score'] = df['Packaging_Option'].map(STRENGTH_MAP).fillna(50)

    # ── Add Product_Category ─────────────────────────────────────────────────
    df['Product_Category'] = df.apply(assign_category, axis=1)

    # ── Feature Engineering ──────────────────────────────────────────────────
    # CO2 Impact Index (0–100, lower = better, so invert)
    max_co2 = df['LCA_Emission_kgCO2'].max()
    df['CO2_Impact_Index'] = round((1 - df['LCA_Emission_kgCO2'] / max_co2) * 100, 2)

    # Cost Efficiency Index (0–100, lower cost = higher score)
    max_cost = df['Cost_per_unit'].max()
    df['Cost_Efficiency_Index'] = round((1 - df['Cost_per_unit'] / max_cost) * 100, 2)

    # Recyclable binary
    df['Recyclable_Binary'] = (df['Recyclable'] == 'Yes').astype(int)

    # Material Suitability Score (composite)
    df['Material_Suitability_Score'] = round(
        0.30 * df['CO2_Impact_Index'] +
        0.25 * df['Biodegradability_Score'] +
        0.25 * df['Cost_Efficiency_Index'] +
        0.20 * df['Strength_Score'],
        2
    )

    # ── Handle duplicates & validate ─────────────────────────────────────────
    before = len(df)
    df.drop_duplicates(subset=['Product_ID'], inplace=True)
    after = len(df)
    if before != after:
        print(f"Removed {before - after} duplicate rows.")

    print(f"[OK] Dataset enhanced: {len(df)} rows, {len(df.columns)} columns")
    return df


def encode_and_scale(df):
    """Encode categoricals + scale numerics for ML training."""
    df_ml = df.copy()

    cat_cols = ['Material_Type', 'Fragility', 'Recyclable', 'Transport_Mode',
                'Product_Category', 'Packaging_Option']
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df_ml[col + '_enc'] = le.fit_transform(df_ml[col])
        encoders[col] = le

    num_cols = ['Product_Weight_g', 'LCA_Emission_kgCO2', 'Cost_per_unit',
                'Biodegradability_Score', 'Strength_Score',
                'CO2_Impact_Index', 'Cost_Efficiency_Index',
                'Material_Suitability_Score']
    scaler = MinMaxScaler()
    df_ml[num_cols] = scaler.fit_transform(df_ml[num_cols])

    return df_ml, encoders, scaler


def run():
    df = load_and_enhance()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"[Saved] {OUTPUT_PATH}")
    print("\nColumn summary:")
    print(df.dtypes)
    print("\nSample (3 rows):")
    print(df.head(3).to_string())
    return df


if __name__ == '__main__':
    run()
