"""Coefficient extraction, ranking, and CSV export."""

import os
import numpy as np
import pandas as pd


def extract_results(model, scaler, feature_names, feature_types, feature_counts):
    """Extract coefficients scaled back to original feature space.
    
    Returns a DataFrame with columns: feature, type, coefficient, odds_multiplier, count.
    """
    # Coefficients are in scaled space; adjust back:
    # model learned w on scaled X. scaled X = X / scale_.
    # So effective coef on original X is w / scale_.
    scale = scaler.scale_
    raw_coefs = model.coef_.flatten()
    coefs = raw_coefs / scale

    df = pd.DataFrame({
        "feature": feature_names,
        "type": feature_types,
        "coefficient": coefs,
        "odds_multiplier": np.exp(coefs),
        "count": feature_counts,
    })
    return df


def save_results(results_df, prefix, output_dir):
    """Save ranked results to CSV files split by feature type."""
    os.makedirs(output_dir, exist_ok=True)

    # Sort all by absolute coefficient magnitude
    results_df["abs_coef"] = results_df["coefficient"].abs()

    # Card rankings
    cards = results_df[results_df["type"] == "card"].sort_values("abs_coef", ascending=False)
    cards = cards.drop(columns=["abs_coef"])
    path = os.path.join(output_dir, f"{prefix}_card_rankings.csv")
    cards.to_csv(path, index=False)
    print(f"  Saved {len(cards)} card rankings to {path}")

    # Squared terms
    squared = results_df[results_df["type"] == "squared"].sort_values("abs_coef", ascending=False)
    squared = squared.drop(columns=["abs_coef"])
    path = os.path.join(output_dir, f"{prefix}_squared_terms.csv")
    squared.to_csv(path, index=False)
    print(f"  Saved {len(squared)} squared terms to {path}")

    # Pair synergies
    pairs = results_df[results_df["type"] == "pair"].sort_values("abs_coef", ascending=False)
    pairs = pairs.drop(columns=["abs_coef"])
    path = os.path.join(output_dir, f"{prefix}_pair_synergies.csv")
    pairs.to_csv(path, index=False)
    print(f"  Saved {len(pairs)} pair synergies to {path}")

    results_df.drop(columns=["abs_coef"], inplace=True)


def save_metrics(all_metrics, output_dir):
    """Save model evaluation metrics to CSV."""
    os.makedirs(output_dir, exist_ok=True)
    rows = []
    for model_name, metrics in all_metrics.items():
        row = {"model": model_name}
        row.update(metrics)
        rows.append(row)
    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, "model_metrics.csv")
    df.to_csv(path, index=False)
    print(f"  Saved metrics to {path}")
