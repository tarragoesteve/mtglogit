import pandas as pd
import json

# -----------------------------
# LOAD CSV FILES
# -----------------------------

# Card-level data (individual performance)
df_cards = pd.read_csv("../results/drawn_card_rankings.csv")

# Pair data (card interactions)
df_pairs = pd.read_csv("../results/drawn_pair_synergies.csv")

# Self-performance data
df_self = pd.read_csv("../results/drawn_squared_terms.csv")

# -----------------------------
# BUILD NODES
# -----------------------------

# Keep only relevant columns
df_nodes = df_cards[["feature", "odds_multiplier"]].copy()

# Rename for graph usage
df_nodes.columns = ["id", "prob"]

# Self probability per card

# Clean "(repeat)" suffix from self feature names
df_self["id"] = df_self["feature"].str.replace(" (repeat)", "", regex=False)

# Keep only needed columns
df_self = df_self[["id", "odds_multiplier"]].copy()

# Rename for graph usage
df_self.columns = ["id", "self_prob"]

# Merge node + self data
df_nodes = df_nodes.merge(df_self, on="id", how="left")

# Optional: attach image path for D3 rendering
df_nodes["image"] = df_nodes["id"].apply(lambda x: f"https://cards.scryfall.io/art_crop/front/4/0/40bafd2b-acd4-46f0-abb2-139e2918ae99.jpg")

# -----------------------------
# BUILD LINKS FROM PAIR STRING
# -----------------------------

links = []

for _, row in df_pairs.iterrows():
    feature = row["feature"]
    weight = row["odds_multiplier"]

    # Skip invalid rows
    if "×" not in feature:
        continue

    # Split "Card A × Card B"
    source, target = [x.strip() for x in feature.split("×")]

    # Ignore self-loops
    if source == target:
        continue

    links.append({
        "source": source,
        "target": target,
        "weight": float(weight)
    })

df_links = pd.DataFrame(links)

# -----------------------------
# REMOVE DUPLICATES (A-B == B-A)
# -----------------------------

df_links["pair"] = df_links.apply(
    lambda x: tuple(sorted([x["source"], x["target"]])),
    axis=1
)

df_links = df_links.drop_duplicates("pair")

# -----------------------------
# NORMALIZE VALUES (IMPORTANT FOR VISUALIZATION)
# -----------------------------

df_nodes["prob_norm"] = df_nodes["prob"] / df_nodes["prob"].max()
df_nodes["self_prob_norm"] = df_nodes["self_prob"] / df_nodes["self_prob"].max()
df_links["weight_norm"] = df_links["weight"] / df_links["weight"].max()

# -----------------------------
# BUILD FINAL GRAPH STRUCTURE
# -----------------------------

graph = {
    "nodes": df_nodes.to_dict(orient="records"),
    "links": df_links.drop(columns="pair").to_dict(orient="records")
}

# -----------------------------
# EXPORT TO JSON FILE
# -----------------------------

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(graph, f, ensure_ascii=False, indent=2)

print("✅ data.json successfully generated")