import pandas as pd
import json
import requests
import time
from pathlib import Path
import sys

# =============================
# CONFIGURATION
# =============================
CONFIG = {
    # Link weight filter
    "MIN_LINK_WEIGHT": 1.02,

    # Scryfall API settings
    "SCRYFALL_BATCH_SIZE": 20,
    "SCRYFALL_SLEEP": 0.1,

    # Data cleaning
    "SELF_TAG": " (repeat)",
}

# CSV files to look for (patterns)
# Searches for files with these specific suffixes
CSV_FILES = {
    "card_rankings": "_card_rankings.csv",
    "pair_synergies": "_pair_synergies.csv",
    "squared_terms": "_squared_terms.csv",
}

def process_results_folder(results_folder_path):
    """
    Process a single results folder and generate data.json in data/
    """
    
    folder_name = results_folder_path.name
    print(f"\n{'='*60}")
    print(f"📊 Processing: {folder_name}")
    print(f"{'='*60}")
    
    # Find the CSV files with preference for "drawn_without_basics"
    csv_files = {}
    for key, filename_pattern in CSV_FILES.items():
        # Look for all files that match the pattern
        matches = list(results_folder_path.glob(f"*{filename_pattern}"))
        
        if not matches:
            print(f"⚠️  {filename_pattern} not found in {folder_name}")
            return False
        
        # Prefer "drawn_without_basics" if available, otherwise use first match
        preferred = [f for f in matches if "drawn_without_basics" in f.name]
        csv_files[key] = preferred[0] if preferred else matches[0]
        
        print(f"   ✓ {key}: {csv_files[key].name}")
    
    try:
        # Load CSV files
        df_cards = pd.read_csv(csv_files["card_rankings"])
        df_pairs = pd.read_csv(csv_files["pair_synergies"])
        df_self = pd.read_csv(csv_files["squared_terms"])
        
        print(f"✅ CSVs loaded ({len(df_cards)} cards, {len(df_pairs)} pairs)")
        
    except Exception as e:
        print(f"❌ Error loading CSVs: {e}")
        return False
    
    # -------- BUILD NODES --------
    df_nodes = df_cards[["feature", "odds_multiplier"]].copy()
    df_nodes.columns = ["id", "prob"]
    
    # -------- CLEAN SELF SCORES --------
    df_self["id"] = df_self["feature"].str.replace(CONFIG["SELF_TAG"], "", regex=False)
    df_self = df_self[["id", "odds_multiplier"]].copy()
    df_self.columns = ["id", "self_prob"]
    
    df_nodes = df_nodes.merge(df_self, on="id", how="left")
    
    # -------- FETCH CARD IMAGES FROM SCRYFALL --------
    card_names = df_nodes["id"].dropna().unique().tolist()
    lookup = {}
    
    for i in range(0, len(card_names), CONFIG["SCRYFALL_BATCH_SIZE"]):
        
        batch = card_names[i:i + CONFIG["SCRYFALL_BATCH_SIZE"]]
        query = " OR ".join([f'"{name}"' for name in batch])
        
        url = (
            "https://api.scryfall.com/cards/search"
            f"?q={requests.utils.quote(query)}"
            "&unique=cards"
        )
        
        print(f"🔎 Fetching {i} → {i+len(batch)}")
        
        try:
            res = requests.get(url).json()
        except Exception as e:
            print(f"⚠️  Error fetching from Scryfall: {e}")
            continue
        
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
        
        time.sleep(CONFIG["SCRYFALL_SLEEP"])
    
    # -------- APPLY CARD IMAGES --------
    df_nodes["card_image"] = df_nodes["id"].map(lambda x: lookup.get(x, {}).get("image"))
    df_nodes["image"] = df_nodes["id"].map(lambda x: lookup.get(x, {}).get("art"))
    
    df_nodes["image"] = df_nodes["image"].fillna("")
    df_nodes["card_image"] = df_nodes["card_image"].fillna("")
    
    # -------- BUILD LINKS --------
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
    
    # -------- REMOVE DUPLICATE LINKS (A-B == B-A) --------
    df_links["pair"] = df_links.apply(
        lambda x: tuple(sorted([x["source"], x["target"]])),
        axis=1
    )
    
    df_links = df_links.drop_duplicates("pair")
    
    # -------- FILTER OUT WEAK LINKS --------
    df_links = df_links[
        df_links["weight"] >= CONFIG["MIN_LINK_WEIGHT"]
    ]
    
    # -------- NORMALIZE VALUES --------
    
    # Node size normalization
    df_nodes["prob_norm"] = (
        (df_nodes["prob"] - df_nodes["prob"].min()) /
        (df_nodes["prob"].max() - df_nodes["prob"].min())
    )
    
    # Self probability normalization
    df_nodes["self_prob_norm"] = df_nodes["self_prob"]
    
    # Link weight normalization
    df_links["weight_norm"] = (
        (df_links["weight"] - df_links["weight"].min()) /
        (df_links["weight"].max() - df_links["weight"].min())
    )
    
    # -------- EXPORT DATA --------
    
    # Create data folder if doesn't exist
    data_folder = Path("data") / folder_name
    data_folder.mkdir(parents=True, exist_ok=True)
    
    graph = {
        "nodes": df_nodes.to_dict(orient="records"),
        "links": df_links.drop(columns="pair").to_dict(orient="records")
    }
    
    output_file = data_folder / "data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"✅ data.json generated in data/{folder_name}/")
    return True


def main():
    results_dir = Path("../results")
    
    if not results_dir.exists():
        print(f"❌ Error: '../results' folder does not exist")
        sys.exit(1)
    
    # Find all subdirectories in results/
    result_folders = [
        f for f in results_dir.iterdir()
        if f.is_dir() and not f.name.startswith(".")
    ]
    
    if not result_folders:
        print("⚠️  No folders found in results/")
        sys.exit(1)
    
    print(f"🔍 Found {len(result_folders)} folder(s) in results/")
    
    success_count = 0
    for folder in sorted(result_folders):
        if process_results_folder(folder):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Completed: {success_count}/{len(result_folders)} folders processed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()