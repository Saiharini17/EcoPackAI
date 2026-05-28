"""
Module 3 & 4: ML Dataset Preparation + AI Recommendation Model
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    accuracy_score,
)
from xgboost import XGBRegressor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "..", "data", "processed_dataset.csv")
MODELS_DIR = os.path.join(BASE, "..", "models")

FEATURES_REG = [
    "Product_Weight_g",
    "Biodegradability_Score",
    "Strength_Score",
    "LCA_Emission_kgCO2",
    "Recyclable_Binary",
    "Material_Type_enc",
    "Fragility_enc",
    "Transport_Mode_enc",
    "Product_Category_enc",
]
FEATURES_CLS = FEATURES_REG + ["Cost_per_unit"]


def load_data():
    if not os.path.exists(DATA_PATH):
        from .data_preparation import load_and_enhance

        df = load_and_enhance()
        df.to_csv(DATA_PATH, index=False)
    return pd.read_csv(DATA_PATH)


def encode(df):
    df = df.copy()
    encoders = {}
    for col in [
        "Material_Type",
        "Fragility",
        "Recyclable",
        "Transport_Mode",
        "Product_Category",
    ]:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    le_t = LabelEncoder()
    df["Packaging_Option_enc"] = le_t.fit_transform(df["Packaging_Option"])
    encoders["Packaging_Option"] = le_t
    return df, encoders


def train():
    os.makedirs(MODELS_DIR, exist_ok=True)
    print("Loading dataset...")
    df = load_data()
    print("Encoding...")
    df, encoders = encode(df)

    X_c, y_c = df[FEATURES_REG], df["Cost_per_unit"]
    Xtr, Xte, ytr, yte = train_test_split(X_c, y_c, test_size=0.2, random_state=42)
    rf_cost = RandomForestRegressor(
        n_estimators=150, max_depth=10, random_state=42, n_jobs=-1
    )
    rf_cost.fit(Xtr, ytr)
    m1 = {
        "rmse": round(float(np.sqrt(mean_squared_error(yte, rf_cost.predict(Xte)))), 4),
        "mae": round(float(mean_absolute_error(yte, rf_cost.predict(Xte))), 4),
        "r2": round(float(r2_score(yte, rf_cost.predict(Xte))), 4),
    }
    print(f"RF Cost -> RMSE:{m1['rmse']} MAE:{m1['mae']} R2:{m1['r2']}")

    X_x, y_x = df[FEATURES_REG], df["LCA_Emission_kgCO2"]
    Xtr2, Xte2, ytr2, yte2 = train_test_split(X_x, y_x, test_size=0.2, random_state=42)
    xgb = XGBRegressor(
        n_estimators=150, max_depth=6, learning_rate=0.1, random_state=42, verbosity=0
    )
    xgb.fit(Xtr2, ytr2)
    m2 = {
        "rmse": round(float(np.sqrt(mean_squared_error(yte2, xgb.predict(Xte2)))), 4),
        "mae": round(float(mean_absolute_error(yte2, xgb.predict(Xte2))), 4),
        "r2": round(float(r2_score(yte2, xgb.predict(Xte2))), 4),
    }
    print(f"XGB CO2 -> RMSE:{m2['rmse']} MAE:{m2['mae']} R2:{m2['r2']}")

    X_p, y_p = df[FEATURES_CLS], df["Packaging_Option_enc"]
    Xtr3, Xte3, ytr3, yte3 = train_test_split(
        X_p, y_p, test_size=0.2, random_state=42, stratify=y_p
    )
    rf_cls = RandomForestClassifier(
        n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
    )
    rf_cls.fit(Xtr3, ytr3)
    acc = round(float(accuracy_score(yte3, rf_cls.predict(Xte3))), 4)
    print(f"RF Classifier -> Accuracy:{acc}")

    arts = {
        "rf_cost": rf_cost,
        "xgb_co2": xgb,
        "rf_cls": rf_cls,
        "encoders": encoders,
        "features_reg": FEATURES_REG,
        "features_cls": FEATURES_CLS,
        "metrics": {"cost": m1, "co2": m2, "classifier_accuracy": acc},
    }
    with open(os.path.join(MODELS_DIR, "ecopackai_models.pkl"), "wb") as f:
        pickle.dump(arts, f)
    print("Models saved.")
    return arts


def load_models():
    p = os.path.join(MODELS_DIR, "ecopackai_models.pkl")
    if not os.path.exists(p):
        return train()
    with open(p, "rb") as f:
        return pickle.load(f)


def recommend(
    product_weight_g,
    material_type,
    fragility,
    recyclable,
    transport_mode,
    product_category,
    top_n=3,
):
    arts = load_models()
    enc = arts["encoders"]

    def se(e, v):
        cls = list(e.classes_)
        return int(e.transform([v if v in cls else cls[0]])[0])

    mat_e = se(enc["Material_Type"], material_type)
    fra_e = se(enc["Fragility"], fragility)
    trn_e = se(enc["Transport_Mode"], transport_mode)
    cat_e = se(enc["Product_Category"], product_category)
    rec_b = 1 if recyclable == "Yes" else 0

    feat_reg = pd.DataFrame(
        [
            [
                float(product_weight_g),
                50.0,
                60.0,
                0.0,
                float(rec_b),
                float(mat_e),
                float(fra_e),
                float(trn_e),
                float(cat_e),
            ]
        ],
        columns=FEATURES_REG,
    )
    base_co2 = float(arts["xgb_co2"].predict(feat_reg)[0])
    feat_reg = feat_reg.copy()
    feat_reg["LCA_Emission_kgCO2"] = base_co2
    pred_cost = float(arts["rf_cost"].predict(feat_reg)[0])

    feat_cls = feat_reg.copy()
    feat_cls["Cost_per_unit"] = pred_cost
    feat_cls = feat_cls[FEATURES_CLS]
    proba = arts["rf_cls"].predict_proba(feat_cls)[0]
    classes = enc["Packaging_Option"].classes_

    results = []
    for i, pkg in enumerate(classes):
        prob = float(proba[i])
        co2_s = max(0.0, 100.0 - base_co2 * 25)
        cost_s = max(0.0, 100.0 - pred_cost * 50)
        suit = round(0.4 * prob * 100 + 0.3 * co2_s + 0.3 * cost_s, 2)
        results.append(
            {
                "packaging_option": pkg,
                "confidence": round(prob * 100, 1),
                "predicted_cost_usd": round(pred_cost, 2),
                "predicted_co2_kg": round(base_co2, 3),
                "suitability_score": suit,
            }
        )
    results.sort(key=lambda x: x["suitability_score"], reverse=True)
    for i, r in enumerate(results[:top_n]):
        r["rank"] = i + 1
    return results[:top_n]


if __name__ == "__main__":
    train()
