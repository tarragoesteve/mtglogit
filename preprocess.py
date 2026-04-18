"""Data loading and preprocessing for MTG win-rate modeling."""

import pandas as pd
import numpy as np


def load_data(csv_path: str) -> pd.DataFrame:
    """Load the CSV and return only relevant columns (won + deck_* + drawn_*)."""
    df = pd.read_csv(csv_path)
    won_col = ["won"]
    deck_cols = [c for c in df.columns if c.startswith("deck_")]
    drawn_cols = [c for c in df.columns if c.startswith("drawn_")]
    df = df[won_col + deck_cols + drawn_cols].copy()

    # Convert won to int (handles True/False strings and bools)
    df["won"] = df["won"].map({"True": 1, "False": 0, True: 1, False: 0}).astype(int)

    # Ensure card columns are numeric
    card_cols = deck_cols + drawn_cols
    df[card_cols] = df[card_cols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

    # Drop rows where won is missing
    df.dropna(subset=["won"], inplace=True)

    print(f"Loaded {len(df)} games, {len(deck_cols)} deck columns, {len(drawn_cols)} drawn columns")
    return df


def split_by_prefix(df: pd.DataFrame, prefix: str, exclude_cards=None):
    """Extract target and feature columns for a given prefix (deck_ or drawn_).
    
    Args:
        exclude_cards: list of card names to drop (without prefix).
    """
    feature_cols = [c for c in df.columns if c.startswith(prefix)]
    if exclude_cards:
        exclude_set = {f"{prefix}{name}" for name in exclude_cards}
        feature_cols = [c for c in feature_cols if c not in exclude_set]
    y = df["won"].values
    X_df = df[feature_cols]
    # Strip prefix from card names for cleaner output
    card_names = [c[len(prefix):] for c in feature_cols]
    return X_df.values, y, card_names
