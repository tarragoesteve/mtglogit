import pandas as pd
import json
import requests
import time
import gzip
import io
import re
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
SCRYFALL_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCRYFALL_HEADERS = {
    "User-Agent": "mtglogit/1.0",
    "Accept": "application/json",
}
CARD_TYPES = (
    "Creature", "Instant", "Sorcery", "Artifact", "Enchantment",
    "Land", "Planeswalker", "Battle", "Kindred",
)


def card_metadata(card):
    """Include major types from either face, but not creature subtypes."""
    type_lines = [card.get("type_line", "")]
    type_lines.extend(face.get("type_line", "") for face in card.get("card_faces", []))
    words = set()
    for line in type_lines:
        for face_line in line.split("//"):
            words.update(re.split(r"\s+", face_line.split("—", 1)[0].strip()))
    return {
        "types": [name for name in CARD_TYPES if name in words],
        "rarity": card.get("rarity"),
    }


def find_card_metadata(name, lookup):
    data = lookup.get(name)
    if data is None:
        normalized = normalize_name(name)
        data = next(
            (value for key, value in lookup.items() if normalize_name(key) == normalized),
            {},
        )
    return {"types": data.get("types", []), "rarity": data.get("rarity")}


def read_bulk_cards(stream):
    """Read current JSON Lines exports and legacy JSON arrays."""
    for line in stream:
        if not line.strip():
            continue
        if line.lstrip().startswith("["):
            yield from json.loads(line + stream.read())
            return
        yield json.loads(line)


def load_bulk_cards():
    archives = sorted(SCRYFALL_DATA_DIR.glob("oracle-cards-*.jsonl.gz"), reverse=True)
    if archives:
        archive = archives[0]
        print(f"Loading local Scryfall bulk data: {archive}")
        with gzip.open(archive, "rt", encoding="utf-8") as stream:
            yield from read_bulk_cards(stream)
        return

    print("Fetching Scryfall Oracle Cards metadata...")
    metadata = requests.get(
        "https://api.scryfall.com/bulk-data/oracle-cards",
        headers=SCRYFALL_HEADERS,
        timeout=60,
    )
    metadata.raise_for_status()
    bulk_data = metadata.json()
    download_url = bulk_data.get("jsonl_download_uri") or bulk_data.get("download_uri")
    if not download_url:
        raise ValueError("Scryfall Oracle Cards metadata has no download URL")

    print(f"Downloading Scryfall Oracle Cards: {download_url}")
    with requests.get(
        download_url, headers=SCRYFALL_HEADERS, timeout=120
    ) as response:
        response.raise_for_status()
        content = response.content
    if content.startswith(b"\x1f\x8b"):
        with gzip.open(io.BytesIO(content), "rt", encoding="utf-8") as stream:
            yield from read_bulk_cards(stream)
    else:
        with io.StringIO(content.decode("utf-8")) as stream:
            yield from read_bulk_cards(stream)

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
    
    try:
        # Build lookup by card name, prioritizing versions with images
        lookup = {}
        for card in load_bulk_cards():
            if card.get("layout") == "art_series":
                continue
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
                **card_metadata(card),
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
            else:
                # A face alias may precede the actual card in the archive.
                lookup[name].update(card_metadata(card))
            
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
            
            # CSVs may use a face name rather than the combined Scryfall name.
            for face in card.get("card_faces", []):
                face_image_uris = face.get("image_uris", {})
                face_data = {
                    **card_metadata(card),
                    "art": face_image_uris.get("art_crop"),
                    "image": face_image_uris.get("normal"),
                    "image_status": image_status,
                    "highres": highres,
                } if face_image_uris.get("normal") else card_data
                for alias in (face.get("name"), face.get("printed_name")):
                    if alias and (alias not in lookup or not lookup[alias].get("image")):
                        lookup[alias] = face_data

        if not lookup:
            raise ValueError("Scryfall bulk data contains no cards")
        _SCRYFALL_CACHE = lookup
        print(f"✅ Loaded {len(lookup)} cards from Scryfall")
        return lookup
        
    except (requests.RequestException, OSError, ValueError, EOFError) as e:
        print(f"❌ Error fetching bulk data: {e}")
        raise


def fetch_card_individually(card_name, lookup):
    """
    Fetch a single card from the Scryfall API by fuzzy name search.
    Used as a fallback for cards missing from oracle_cards bulk data.
    """
    try:
        url = "https://api.scryfall.com/cards/named"
        resp = requests.get(
            url, params={"fuzzy": card_name}, headers=SCRYFALL_HEADERS, timeout=60
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        
        card = resp.json()
        image_uris = {}
        
        if "card_faces" in card and len(card["card_faces"]) > 0:
            image_uris = card["card_faces"][0].get("image_uris", {})
        if not image_uris.get("normal"):
            image_uris = card.get("image_uris", {})
        
        card_data = {
            **card_metadata(card),
            "art": image_uris.get("art_crop"),
            "image": image_uris.get("normal"),
            "image_status": card.get("image_status"),
            "highres": card.get("highres_image", False),
        }
        
        lookup[card_name] = card_data
        return card_data
        
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️  Failed to fetch '{card_name}' individually: {e}")
        return None

def build_table_data(df_cards, df_self, df_pairs):
    """Keep all modeled weights and their feature-specific game counts."""
    alone = df_cards[["feature", "odds_multiplier", "count"]].copy()
    alone.columns = ["card", "weight", "games"]

    repeats = df_self[["feature", "odds_multiplier", "count"]].copy()
    repeats.columns = ["card", "weight", "games"]
    repeats["card"] = repeats["card"].str.removesuffix(CONFIG["SELF_TAG"])

    pairs = []
    seen = set()
    for row in df_pairs.itertuples(index=False):
        source, target = [name.strip() for name in row.feature.split("×")]
        key = tuple(sorted((source, target)))
        if source == target or key in seen:
            continue
        seen.add(key)
        pairs.append({
            "source": source,
            "target": target,
            "weight": float(row.odds_multiplier),
            "games": int(row.count),
        })

    return {
        "alone": alone.to_dict(orient="records"),
        "self": repeats.to_dict(orient="records"),
        "pairs": pairs,
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
    
    tables = build_table_data(df_cards, df_self, df_pairs)

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

    metadata = [find_card_metadata(name, lookup) for name in df_nodes["id"]]
    df_nodes["types"] = [card["types"] for card in metadata]
    df_nodes["rarity"] = [card["rarity"] for card in metadata]
    
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
        "links": df_links.drop(columns="pair").to_dict(orient="records"),
        "tables": tables,
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