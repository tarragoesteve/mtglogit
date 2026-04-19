import pandas as pd
import json
import requests
import time
import gzip
import io
import unicodedata
from pathlib import Path
import sys

# =============================
# CONFIGURATION
# =============================
CONFIG = {
    # Link weight filter
    "MIN_LINK_WEIGHT": 1.01,

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

# Global variable to cache bulk data across folders
_SCRYFALL_CACHE = None

def normalize_name(name):
    """Remove diacritics and special characters for fuzzy matching"""
    # Remove diacritics first
    nfkd_form = unicodedata.normalize('NFKD', name)
    name_without_diacritics = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # Common special character mappings
    replacements = {
        'ō': 'o', 'Ō': 'O',
        'ă': 'a', 'Ă': 'A',
        'ç': 'c', 'Ç': 'C',
        'é': 'e', 'É': 'E',
        'á': 'a', 'Á': 'A',
        'ñ': 'n', 'Ñ': 'N',
        '?': '',  # Remove ?
    }
    
    for old, new in replacements.items():
        name_without_diacritics = name_without_diacritics.replace(old, new)
    
    # Remove any remaining non-ASCII characters
    name_without_diacritics = name_without_diacritics.encode('ascii', errors='ignore').decode('ascii')
    
    return name_without_diacritics

def fetch_scryfall_bulk_data():
    """
    Download and parse Scryfall bulk data (Oracle Cards).
    Returns a dictionary indexed by card name.
    """
    global _SCRYFALL_CACHE
    
    if _SCRYFALL_CACHE is not None:
        return _SCRYFALL_CACHE
    
    print("🌐 Fetching Scryfall bulk data index...")
    
    try:
        # Get the list of bulk data files
        bulk_list_url = "https://api.scryfall.com/bulk-data"
        bulk_list = requests.get(bulk_list_url).json()
        
        # Find the oracle_cards file (one entry per card name)
        bulk_data = None
        for item in bulk_list.get("data", []):
            if item.get("type") == "oracle_cards":
                bulk_data = item
                break
        
        if not bulk_data:
            print("⚠️  Oracle cards bulk data not found")
            return {}
        
        download_url = bulk_data.get("download_uri")
        if not download_url:
            print("⚠️  Download URL not found")
            return {}
        
        print(f"📥 Downloading oracle cards (~{bulk_data.get('size', 0) // (1024*1024)} MB)...")
        
        # Download the file
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # Try to decompress as gzip, if it fails, parse as JSON directly
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
                cards_data = json.load(gz)
        except (OSError, gzip.BadGzipFile):
            # File is already decompressed, parse directly
            cards_data = json.loads(response.content.decode('utf-8'))
        
        # Build lookup by card name, prioritizing versions with images
        lookup = {}
        for card in cards_data:
            name = card.get("name")
            printed_name = card.get("printed_name")
            image_uris = {}
            
            # Try front face first (double-faced cards)
            if "card_faces" in card and len(card["card_faces"]) > 0:
                image_uris = card["card_faces"][0].get("image_uris", {})
            
            # If no image yet, try default image_uris
            if not image_uris.get("normal"):
                image_uris = card.get("image_uris", {})
            
            image_url = image_uris.get("normal")
            image_status = card.get("image_status")
            highres = card.get("highres_image", False)
            
            card_data = {
                "art": image_uris.get("art_crop"),
                "image": image_url,
                "image_status": image_status,
                "highres": highres
            }
            
            # Store if:
            # 1. We have an image and it's the first time seeing this name
            # 2. Or if we have a better image (highres, highres_scan status, etc)
            should_update = False
            if name not in lookup:
                should_update = True
            elif image_url and not lookup[name].get("image"):
                # Previous was empty, new one has image
                should_update = True
            elif highres and not lookup[name].get("highres"):
                # New one is highres, previous wasn't
                should_update = True
            elif image_status == "highres_scan" and lookup[name].get("image_status") != "highres_scan":
                # New one has highres_scan status
                should_update = True
            
            if should_update:
                lookup[name] = card_data
            
            # Also store by printed_name if it's different
            if printed_name and printed_name != name:
                should_update_printed = False
                if printed_name not in lookup:
                    should_update_printed = True
                elif image_url and not lookup[printed_name].get("image"):
                    should_update_printed = True
                elif highres and not lookup[printed_name].get("highres"):
                    should_update_printed = True
                elif image_status == "highres_scan" and lookup[printed_name].get("image_status") != "highres_scan":
                    should_update_printed = True
                
                if should_update_printed:
                    lookup[printed_name] = card_data
            
            # Also check card_faces for printed names (important for modal DFCs)
            if "card_faces" in card:
                for face in card["card_faces"]:
                    face_printed_name = face.get("printed_name")
                    face_image_uris = face.get("image_uris", {})
                    
                    if face_printed_name and face_image_uris.get("normal"):
                        should_update_face = False
                        if face_printed_name not in lookup:
                            should_update_face = True
                        elif not lookup[face_printed_name].get("image"):
                            should_update_face = True
                        elif face.get("image_uris", {}).get("normal") and not lookup[face_printed_name].get("image"):
                            should_update_face = True
                        
                        if should_update_face:
                            lookup[face_printed_name] = {
                                "art": face_image_uris.get("art_crop"),
                                "image": face_image_uris.get("normal"),
                                "image_status": card.get("image_status"),
                                "highres": card.get("highres_image", False)
                            }
        
        _SCRYFALL_CACHE = lookup
        print(f"✅ Loaded {len(lookup)} cards from Scryfall")
        return lookup
        
    except Exception as e:
        print(f"❌ Error fetching bulk data: {e}")
        return {}


def fetch_card_individually(card_name, lookup):
    """
    Fetch a single card from the Scryfall API by fuzzy name search.
    Used as a fallback for cards missing from oracle_cards bulk data.
    """
    try:
        url = "https://api.scryfall.com/cards/named"
        resp = requests.get(url, params={"fuzzy": card_name})
        if resp.status_code != 200:
            return None
        
        card = resp.json()
        image_uris = {}
        
        if "card_faces" in card and len(card["card_faces"]) > 0:
            image_uris = card["card_faces"][0].get("image_uris", {})
        if not image_uris.get("normal"):
            image_uris = card.get("image_uris", {})
        
        card_data = {
            "art": image_uris.get("art_crop"),
            "image": image_uris.get("normal"),
            "image_status": card.get("image_status"),
            "highres": card.get("highres_image", False),
        }
        
        lookup[card_name] = card_data
        return card_data
        
    except Exception as e:
        print(f"⚠️  Failed to fetch '{card_name}' individually: {e}")
        return None

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
    
    # -------- FETCH CARD IMAGES FROM SCRYFALL (single bulk request) --------
    lookup = fetch_scryfall_bulk_data()
    
    # -------- FETCH MISSING CARDS INDIVIDUALLY --------
    all_card_names = df_nodes["id"].tolist()
    missing = [n for n in all_card_names if n not in lookup]
    if missing:
        print(f"🔎 Fetching {len(missing)} card(s) not in oracle_cards individually...")
        for card_name in missing:
            result = fetch_card_individually(card_name, lookup)
            if result and result.get("image"):
                print(f"   ✓ Found: {card_name}")
            else:
                print(f"   ✗ Not found: {card_name}")
            time.sleep(CONFIG["SCRYFALL_SLEEP"])
    
    # -------- APPLY CARD IMAGES WITH NAME FALLBACK --------
    def get_card_image(card_name):
        """Try to find card image, with multiple fallback strategies"""
        # Strategy 1: Exact match
        if card_name in lookup:
            return lookup[card_name].get("image")
        
        # Strategy 2: Remove special characters
        clean_name = card_name.replace("'", "'").replace("'", "'")
        if clean_name in lookup and clean_name != card_name:
            return lookup[clean_name].get("image")
        
        # Strategy 3: Replace em-dash with hyphen
        dash_name = card_name.replace("—", "-")
        if dash_name in lookup and dash_name != card_name:
            return lookup[dash_name].get("image")
        
        # Strategy 4: Normalize diacritics (remove accents, handle special chars)
        normalized_card = normalize_name(card_name)
        if normalized_card:  # Only if normalization resulted in something
            for scryfall_name, data in lookup.items():
                if normalize_name(scryfall_name) == normalized_card and data.get("image"):
                    return data.get("image")
        
        # Strategy 5: Fuzzy match for names with ? (corrupted character)
        # Try to match with the normalized prefix
        if '?' in card_name:
            prefix = card_name.split('?')[0].strip()
            for scryfall_name, data in lookup.items():
                if scryfall_name.startswith(prefix) and data.get("image"):
                    return data.get("image")
        
        # Strategy 6: Partial match (exact substring)
        for scryfall_name, data in lookup.items():
            if card_name in scryfall_name and data.get("image"):
                return data.get("image")
        
        # Strategy 7: Substring match from scryfall side (reverse)
        for scryfall_name, data in lookup.items():
            if scryfall_name in card_name and data.get("image"):
                return data.get("image")
        
        # Strategy 8: Case-insensitive partial match
        card_name_lower = card_name.lower()
        for scryfall_name, data in lookup.items():
            if card_name_lower in scryfall_name.lower() and data.get("image"):
                return data.get("image")
        
        return None
    
    def get_card_art(card_name):
        """Try to find card art, with multiple fallback strategies"""
        # Strategy 1: Exact match
        if card_name in lookup:
            return lookup[card_name].get("art")
        
        # Strategy 2: Remove special characters
        clean_name = card_name.replace("'", "'").replace("'", "'")
        if clean_name in lookup and clean_name != card_name:
            return lookup[clean_name].get("art")
        
        # Strategy 3: Replace em-dash with hyphen
        dash_name = card_name.replace("—", "-")
        if dash_name in lookup and dash_name != card_name:
            return lookup[dash_name].get("art")
        
        # Strategy 4: Normalize diacritics (remove accents, handle special chars)
        normalized_card = normalize_name(card_name)
        if normalized_card:  # Only if normalization resulted in something
            for scryfall_name, data in lookup.items():
                if normalize_name(scryfall_name) == normalized_card and data.get("art"):
                    return data.get("art")
        
        # Strategy 5: Fuzzy match for names with ? (corrupted character)
        # Try to match with the normalized prefix
        if '?' in card_name:
            prefix = card_name.split('?')[0].strip()
            for scryfall_name, data in lookup.items():
                if scryfall_name.startswith(prefix) and data.get("art"):
                    return data.get("art")
        
        # Strategy 6: Partial match (exact substring)
        for scryfall_name, data in lookup.items():
            if card_name in scryfall_name and data.get("art"):
                return data.get("art")
        
        # Strategy 7: Substring match from scryfall side (reverse)
        for scryfall_name, data in lookup.items():
            if scryfall_name in card_name and data.get("art"):
                return data.get("art")
        
        # Strategy 8: Case-insensitive partial match
        card_name_lower = card_name.lower()
        for scryfall_name, data in lookup.items():
            if card_name_lower in scryfall_name.lower() and data.get("art"):
                return data.get("art")
        
        return None
    
    df_nodes["card_image"] = df_nodes["id"].map(get_card_image)
    df_nodes["image"] = df_nodes["id"].map(get_card_art)
    
    df_nodes["image"] = df_nodes["image"].fillna("")
    df_nodes["card_image"] = df_nodes["card_image"].fillna("")
    
    # -------- REPORT MISSING IMAGES AND MISSING CARDS --------
    missing_cards = df_nodes[df_nodes["card_image"] == ""]
    if len(missing_cards) > 0:
        print(f"⚠️  {len(missing_cards)} card(s) without images:")
        for idx, row in missing_cards.iterrows():
            in_lookup = row['id'] in lookup
            lookup_status = "(in Scryfall but no image)" if in_lookup else "(not in Scryfall)"
            print(f"     - {row['id']} {lookup_status}")
    
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