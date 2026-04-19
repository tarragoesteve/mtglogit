"""Main entry point: orchestrate the full pipeline for deck and drawn models."""

import argparse
import os
import glob

from preprocess import load_data, split_by_prefix
from features import build_features
from train import train_model
from analyze import extract_results, save_results, save_metrics


def find_csv(data_dir):
    """Find the first CSV file in the data directory (searches recursively)."""
    pattern = os.path.join(data_dir, "**", "*.csv")
    files = [f for f in glob.glob(pattern, recursive=True) if os.path.isfile(f)]
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    return files[0]


def run_pipeline(prefix, X_raw, y, card_names, args, output_dir):
    """Run the full pipeline for one prefix (deck or drawn)."""
    print(f"\n{'='*60}")
    print(f"Model: {prefix}")
    print(f"{'='*60}")

    print(f"\n[1/3] Feature engineering...")
    X_feat, feat_names, feat_types, feat_counts = build_features(
        X_raw, card_names,
        min_card_freq=args.min_card_freq,
        min_pair_freq=args.min_pair_freq,
        min_repeat_freq=args.min_repeat_freq,
    )

    print(f"\n[2/3] Training model...")
    model, scaler, metrics = train_model(
        X_feat, y,
        l1_ratio=args.l1_ratio,
        C=args.C,
        max_iter=args.max_iter,
    )

    print(f"\n[3/3] Extracting results...")
    results_df = extract_results(model, scaler, feat_names, feat_types, feat_counts)
    save_results(results_df, prefix, output_dir)

    return metrics


def main():
    parser = argparse.ArgumentParser(description="MTG Win-Rate Logistic Regression Model")
    parser.add_argument("--data-dir", default="data", help="Directory containing CSV data")
    parser.add_argument("--output-dir", default="results", help="Directory for output CSVs")
    parser.add_argument("--min-card-freq", type=float, default=0.01,
                        help="Minimum card frequency threshold (default: 0.01)")
    parser.add_argument("--min-pair-freq", type=float, default=0.005,
                        help="Minimum pair co-occurrence frequency (default: 0.005)")
    parser.add_argument("--min-repeat-freq", type=float, default=0.005,
                        help="Minimum repeat (2+ copies) frequency (default: 0.005)")
    parser.add_argument("--l1-ratio", type=float, default=0.5,
                        help="Elastic net L1 ratio (default: 0.5)")
    parser.add_argument("--C", type=float, default=1.0,
                        help="Regularization strength inverse (default: 1.0)")
    parser.add_argument("--max-iter", type=int, default=1000,
                        help="Max solver iterations (default: 1000)")
    parser.add_argument("--all", action="store_true",
                        help="Run all analyses (deck, drawn, drawn_without_basics). Default: only drawn_without_basics")
    args = parser.parse_args()

    BASIC_LANDS = ["Forest", "Island", "Plains", "Swamp", "Mountain"]

    # Find and load data
    csv_path = find_csv(args.data_dir)
    print(f"Using data file: {csv_path}")
    df = load_data(csv_path)

    all_metrics = {}

    if args.all:
        # Run for deck_ columns
        X_deck, y, deck_names = split_by_prefix(df, "deck_")
        metrics_deck = run_pipeline("deck", X_deck, y, deck_names, args, args.output_dir)
        all_metrics["deck"] = metrics_deck

        # Run for drawn_ columns
        X_drawn, y, drawn_names = split_by_prefix(df, "drawn_")
        metrics_drawn = run_pipeline("drawn", X_drawn, y, drawn_names, args, args.output_dir)
        all_metrics["drawn"] = metrics_drawn

    # Run for drawn_ columns without basic lands (default)
    X_drawn_nb, y, drawn_nb_names = split_by_prefix(df, "drawn_", exclude_cards=BASIC_LANDS)
    metrics_drawn_nb = run_pipeline("drawn_without_basics", X_drawn_nb, y, drawn_nb_names, args, args.output_dir)
    all_metrics["drawn_without_basics"] = metrics_drawn_nb

    # Save combined metrics
    print(f"\n{'='*60}")
    print("Saving combined metrics...")
    save_metrics(all_metrics, args.output_dir)

    print(f"\nDone! Results saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
