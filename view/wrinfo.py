import pandas as pd
import json
import requests
import time

# -----------------------------
# LOAD CSV FILES
# -----------------------------
df_cards = pd.read_csv("../results/drawn_without_basics_card_rankings.csv")
df_pairs = pd.read_csv("../results/drawn_without_basics_pair_synergies.csv")
df_self = pd.read_csv("../results/drawn_without_basics_squared_terms.csv")

# -----------------------------
# BUILD NODES
# -----------------------------
df_nodes = df_cards[["feature", "odds_multiplier"]].copy()
df_nodes.columns = ["id", "prob"]

# -----------------------------
# SELF SCORE CLEANING
# -----------------------------
df_self["id"] = df_self["feature"].str.replace(" (repeat)", "", regex=False)
df_self = df_self[["id", "odds_multiplier"]].copy()
df_self.columns = ["id", "self_prob"]

df_nodes = df_nodes.merge(df_self, on="id", how="left")

# -----------------------------
# SCRYFALL IMAGES
# -----------------------------
MAX_BATCH = 20
card_names = df_nodes["id"].dropna().unique().tolist()

lookup = {}

for i in range(0, len(card_names), MAX_BATCH):

    batch = card_names[i:i + MAX_BATCH]
    query = " OR ".join([f'"{name}"' for name in batch])

    url = (
        "https://api.scryfall.com/cards/search"
        f"?q={requests.utils.quote(query)}"
        "&unique=cards"
    )

    print(f"🔎 Fetching {i} → {i+len(batch)}")

    res = requests.get(url).json()

    if "data" not in res:
        continue

    for card in res["data"]:
        name = card.get("name")
        image_uris = card.get("image_uris", {})

        if not image_uris and "card_faces" in card:
            image_uris = card["card_faces"][0].get("image_uris", {})

        lookup[name] = {
            "art": image_uris.get("art_crop"),
            "image": image_uris.get("normal")
        }

    time.sleep(0.1)

# -----------------------------
# APPLY IMAGES
# -----------------------------
df_nodes["card_image"] = df_nodes["id"].map(lambda x: lookup.get(x, {}).get("image"))
df_nodes["image"] = df_nodes["id"].map(lambda x: lookup.get(x, {}).get("art"))

df_nodes["image"] = df_nodes["image"].fillna("")
df_nodes["card_image"] = df_nodes["card_image"].fillna("")

# -----------------------------
# LINKS
# -----------------------------
links = []

for _, row in df_pairs.iterrows():

    feature = row["feature"]
    weight = row["odds_multiplier"]

    if "×" not in feature:
        continue

    source, target = [x.strip() for x in feature.split("×")]

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
# FILTER WEAK LINKS
# -----------------------------
df_links = df_links[df_links["weight"] >= 1.08]

# -----------------------------
# NORMALIZATION (FINAL BALANCED VERSION)
# -----------------------------

# 📏 NODE SIZE
df_nodes["prob_norm"] = (df_nodes["prob"] - df_nodes["prob"].min()) / (df_nodes["prob"].max()- df_nodes["prob"].min())
# ✨ SELF PROB
df_nodes["self_prob_norm"] = df_nodes["self_prob"]
# 🔗 LINKS
df_links["weight_norm"] = (df_links["weight"] - df_links["weight"].min()) / (df_links["weight"].max() - df_links["weight"].min())

# -----------------------------
# EXPORT
# -----------------------------
graph = {
    "nodes": df_nodes.to_dict(orient="records"),
    "links": df_links.drop(columns="pair").to_dict(orient="records")
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(graph, f, ensure_ascii=False, indent=2)

print("✅ FINAL data.json generated")