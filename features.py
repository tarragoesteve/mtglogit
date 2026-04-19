"""Feature engineering: frequency filtering, sparse matrices, pairwise interactions."""

import numpy as np
from scipy import sparse
from itertools import combinations


def filter_cards_by_frequency(X, card_names, min_freq=0.01):
    """Keep only cards appearing in >= min_freq fraction of games.
    
    Returns filtered X, filtered card names, and mask of kept columns.
    """
    n_games = X.shape[0]
    # Card is "present" if count >= 1
    presence = (X >= 1).sum(axis=0)
    if isinstance(presence, np.matrix):
        presence = np.asarray(presence).flatten()
    freq = presence / n_games
    mask = freq >= min_freq
    kept_names = [card_names[i] for i in range(len(card_names)) if mask[i]]
    X_filtered = X[:, mask]
    print(f"  Cards kept: {len(kept_names)} / {len(card_names)} (min_freq={min_freq})")
    return X_filtered, kept_names


def build_features(X, card_names, min_card_freq=0.01, min_pair_freq=0.005, min_repeat_freq=0.005):
    """Build full feature matrix: card counts + repeat terms + filtered pair interactions.
    
    Args:
        min_repeat_freq: minimum fraction of games where a card appears 2+ times
                         for its repeat term to be included.
    Returns:
        X_final: sparse CSR matrix of all features
        feature_names: list of feature name strings
        feature_types: list of feature type strings ('card', 'repeat', 'pair')
        feature_counts: array of nonzero counts per feature
    """
    n_games = X.shape[0]

    # Step 1: Filter cards by frequency
    X_filt, filt_names = filter_cards_by_frequency(X, card_names, min_card_freq)
    n_cards = len(filt_names)

    # Convert to sparse if not already
    if not sparse.issparse(X_filt):
        X_filt = sparse.csr_matrix(X_filt, dtype=np.float64)
    else:
        X_filt = X_filt.astype(np.float64)

    # Step 2: Repeated-card interaction terms: x_i * (x_i - 1)
    # This is 0 for 0-1 copies, and captures self-synergy for 2+ copies
    X_sq_all = X_filt.multiply(X_filt) - X_filt  # x_i^2 - x_i = x_i*(x_i-1), stays sparse

    # Filter repeat terms: keep only cards with 2+ copies in enough games
    min_repeat_count = int(min_repeat_freq * n_games)
    repeat_presence = np.asarray((X_sq_all != 0).sum(axis=0)).flatten()
    repeat_mask = repeat_presence >= min_repeat_count
    X_sq = X_sq_all[:, repeat_mask]
    repeat_names = [filt_names[i] for i in range(n_cards) if repeat_mask[i]]
    n_repeats = len(repeat_names)
    print(f"  Repeat terms kept: {n_repeats} / {n_cards} (min_repeat_freq={min_repeat_freq})")

    # Step 3: Pairwise interactions with frequency filtering
    min_pair_count = int(min_pair_freq * n_games)
    print(f"  Building pairwise features (min co-occurrence: {min_pair_count} games)...")

    # Compute co-occurrence: how many games have both card i and card j present
    presence = (X_filt >= 1).astype(np.float64)
    # co_occur[i,j] = number of games where both i and j are present
    co_occur = (presence.T @ presence).toarray()

    # Find pairs that pass frequency threshold
    pair_indices = []
    pair_names = []
    for i, j in combinations(range(n_cards), 2):
        if co_occur[i, j] >= min_pair_count:
            pair_indices.append((i, j))
            pair_names.append(f"{filt_names[i]} × {filt_names[j]}")

    print(f"  Pairs kept: {len(pair_indices)} (from {n_cards * (n_cards - 1) // 2} possible)")

    # Build sparse pair feature matrix efficiently using column slicing
    if pair_indices:
        # Extract columns as CSC for efficient column access
        X_csc = X_filt.tocsc()
        pair_cols = []
        for i, j in pair_indices:
            # Multiply sparse columns element-wise (stays sparse)
            pair_cols.append(X_csc[:, i].multiply(X_csc[:, j]))
        X_pairs = sparse.hstack(pair_cols, format="csr")
    else:
        X_pairs = sparse.csr_matrix((n_games, 0))

    # Step 4: Combine all features
    X_final = sparse.hstack([X_filt, X_sq, X_pairs], format="csr")

    # Build feature name and type lists
    feature_names = (
        filt_names
        + [f"{name} (repeat)" for name in repeat_names]
        + pair_names
    )
    feature_types = (
        ["card"] * n_cards
        + ["repeat"] * n_repeats
        + ["pair"] * len(pair_indices)
    )

    print(f"  Final feature matrix: {X_final.shape[0]} games × {X_final.shape[1]} features")
    print(f"    Cards: {n_cards}, Repeat: {n_repeats}, Pairs: {len(pair_indices)}")

    # Compute feature frequency counts (number of games where feature is nonzero)
    card_counts = np.asarray((X_filt != 0).sum(axis=0)).flatten()
    repeat_counts_filtered = np.asarray((X_sq != 0).sum(axis=0)).flatten()
    pair_counts = np.asarray((X_pairs != 0).sum(axis=0)).flatten() if pair_indices else np.array([])
    feature_counts = np.concatenate([card_counts, repeat_counts_filtered, pair_counts]).astype(int)

    return X_final, feature_names, feature_types, feature_counts
