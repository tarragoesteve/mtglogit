We are going to create a script that output the odds contribution of each card, and each card pair in a given set of magic.

To do so we will analyze the data in the csv inside /data folder. The columns that start with deck_, indicates the number of cards of that name in the deck. We will also repeat the same analysis for the drawn_. The won column indicates if the match with that deck was won. I want to predict the 

You are a machine learning engineer tasked with building a model to estimate win probability of card decks using observational game data (e.g., from 17Lands).

Objective

Model:
P(win | deck)

using:

Individual card contributions
Pairwise card interaction effects (synergies / anti-synergies)

Decks may contain repeated cards.

Data Description

Each sample represents a game (or deck) with:

A decklist (card IDs with counts)
A binary outcome: win (1) or loss (0)

Assume:

~360 unique cards
~82,000 games
Deck size ~40 cards
Modeling Approach

Use a logistic regression model with pairwise interactions:

logit(P(win | D)) =
β0

Σ β_i * x_i
Σ β_ij * x_i * x_j
(+ optional Σ γ_i * x_i² for repeated-card effects)

Where:

x_i = count of card i in the deck
β_i = individual card strength
β_ij = interaction (synergy) between cards i and j

Use sigmoid to convert log-odds into probability.

Key Constraints
Full pairwise model (~65k parameters) is too large for dataset size
Must reduce dimensionality to avoid overfitting
Feature Engineering
Encode decks as sparse vectors:
Card counts (x_i)
Pair features (x_i * x_j) for all pairs in deck
Use sparse matrix representation
Feature Filtering (CRITICAL)

Apply frequency thresholds:

Keep cards appearing in ≥ 1–2% of decks
Keep pairs appearing in ≥ 0.5% of decks (~400+ occurrences)

This should reduce:

Pairs from ~65k → ~2k–6k
Model Training

Use logistic regression with:

Solver: saga
Regularization: Elastic Net (L1 + L2)
l1_ratio ≈ 0.5 (tunable)
Standardize features if needed
Validation
Train/test split (80/20)
Evaluate:
Log loss
AUC / accuracy

Check for overfitting:

Large gap between train and test → too many features or weak regularization
Output / Interpretation

Extract:

Card strength:
β_i
Pair synergy:
β_ij

Interpretation:

β > 0 → increases win probability
β < 0 → decreases win probability

Convert to odds multiplier:

exp(β)
Practical Notes
Use sparse matrix libraries (e.g., scipy.sparse)
Expect ~0.5–1 GB RAM usage
Training time: ~1–3 minutes after filtering
Extensions (optional)
Add x_i² terms to model diminishing returns or stacking
Use cross-validation to tune regularization
Compare with gradient boosting (LightGBM/XGBoost) for performance
Deliverables

Produce:

Data preprocessing pipeline
Feature construction (cards + filtered pairs)
Model training code
Evaluation metrics
Ranked list of:
Best cards
Strongest synergies

Ensure code is efficient, scalable, and uses sparse representations.

Focus on:

Avoiding overfitting
Extracting reliable pairwise interactions
Producing interpretable results