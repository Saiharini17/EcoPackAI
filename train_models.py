"""
Run this script FIRST before starting the Flask app.
It processes the dataset and trains all ML models.

Usage:
    python train_models.py
"""

from utils.data_preparation import run as prepare_data
from utils.ml_models import train

if __name__ == '__main__':
    print("=" * 50)
    print("  EcoPackAI — Model Training Pipeline")
    print("=" * 50)

    print("\n[1/2] Data preparation & feature engineering...")
    prepare_data()

    print("\n[2/2] Training ML models...")
    arts = train()

    print("\n" + "=" * 50)
    print("DONE! Models ready. Now run:  python app.py")
    print("=" * 50)
