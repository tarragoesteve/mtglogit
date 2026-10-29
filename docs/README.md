# 🎴 MTG LogIt - Data Visualizer

Interactive visualization system for analyzing Magic: The Gathering card data.

## 📋 Structure

```
docs/
├── index.html              # Main page
├── script.js               # Visualization logic (D3.js)
├── wrinfo.py              # Generates data.json from results/
├── generate_datasets.py   # Generates datasets.json
├── init.sh                # Automatic initialization script
├── requirements.txt       # Python dependencies
├── venv/                  # Virtual environment (created by init.sh)
└── data/
    ├── set1/
    │   └── data.json      # Dataset 1 data
    ├── set2/
    │   └── data.json      # Dataset 2 data
    └── [more datasets...]
```

## 🚀 Quick Start

### Automatic Setup (Recommended)

```bash
cd docs/
bash init.sh
source venv/bin/activate
python3 -m http.server
```

**Then open:** http://localhost:8000

---

### Manual Setup

#### 1. Create virtual environment

```bash
cd docs/
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Generate datasets

```bash
python wrinfo.py          # Process all folders in ../results/
python generate_datasets.py   # Update datasets.json
```

#### 4. Start server

```bash
python3 -m http.server
```

---

## ⚙️ Configuration

### Default dataset

In `script.js`, around line ~60:

```javascript
// CHANGE HERE FOR DEFAULT FOLDER
const DEFAULT_DATASET = "set1";
```

Change `"set1"` to any folder name in `data/`.

### URL parameter

You can specify a dataset in the URL:

```
http://localhost:8000/?dataset=data/set2/data.json
```

---

## 🎨 Real-time Configuration

Use the gear icon ⚙️ in the top-right corner to adjust:

- **Table view**: Switch immediately between the graph (default) and the weights table
- **Dataset**: Switch which data is visualized
- **Link Visible Threshold** (1.0 - 2.0): Link visibility sensitivity
- **SELF_PROB High** (1.0 - 1.5): Threshold for green glow
- **SELF_PROB Low** (0.5 - 1.0): Threshold for red glow

Press **Apply** to reload with new parameters.

### Table view

The **Alone**, **Self**, and **Pairs** tabs show card names, weights, and game
counts. Pairs show both card names and include all modeled pairs, including
negative effects; graph link limits and thresholds do not restrict the tables.

- **Weight** is the model's odds multiplier, not its raw coefficient; 1 is neutral.
- **Games** counts games where the card is present (Alone), 2+ copies are present
  (Self), or both cards are present (Pairs), using the modeled game data.
- Click a column header to sort in either direction. Each tab starts with highest
  weight first.
- Hover over a card name (either name in Pairs) to preview its card image.
  Keyboard focus also shows the preview; Escape dismisses it. Missing images
  display an explicit unavailable message.
- **Minimum games** includes rows with at least that many games; 0 includes all
  rows, including zero-count features. Filters and sorting are retained per tab
  while switching views or datasets.
- Changing the view is immediate. Dataset changes still use **Apply**. Graph-only
  controls are hidden in table view, and the graph simulation pauses while hidden.

The generated `data.json` includes a `tables` object alongside the existing graph
nodes and links. Regenerate datasets with `python wrinfo.py` after updating the
exporter so the table weights and counts are available.
Older graph-only datasets still work in graph view; table view displays a
regeneration message until table data is available.

To run the exporter tests from this directory:

```bash
python -m unittest test_wrinfo
```

---

## 📊 Adding New Data

### 1. Create a results folder

```bash
mkdir -p ../results/my_analysis
```

### 2. Add your CSV files

```
../results/my_analysis/
├── *_card_rankings.csv
├── *_pair_synergies.csv
└── *_squared_terms.csv
```

Files must end with these suffixes. Prefixes don't matter.

### 3. Regenerate data

```bash
bash init.sh
```

This automatically creates `data/my_analysis/data.json`.

---

## 🔍 How It Works

### wrinfo.py

1. Scans **all** folders in `results/`
2. For each folder:
   - Reads CSVs with suffixes `_card_rankings.csv`, `_pair_synergies.csv`, `_squared_terms.csv`
   - Prefers files containing `"drawn_without_basics"` if available
   - Fetches card images from Scryfall API
   - Generates `data/{folder_name}/data.json`

### generate_datasets.py

1. Reads all folders in `data/`
2. Verifies each has valid `data.json`
3. Generates `datasets.json` with updated list

### script.js

1. On load, fetches `datasets.json`
2. Populates dataset dropdown
3. Loads default dataset (or from URL param)
4. Allows real-time parameter changes

---

## 🐛 Troubleshooting

### Virtual environment issues

```bash
# If venv doesn't work, delete it and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Data not updating

1. Check you have CSVs in `results/`
2. Run: `python wrinfo.py`
3. Run: `python generate_datasets.py`
4. Reload page in browser (Ctrl+Shift+R for hard refresh)

### Images not loading

- The importer first reads the newest `oracle-cards-*.jsonl.gz` archive in the
  repository-root `data/` folder, independently of the current working directory.
  Put a downloaded [Oracle Cards bulk archive](https://scryfall.com/docs/api/bulk-data)
  there to avoid downloading it again. Remove or replace it when you want fresh data.
- Without a local archive, it downloads Oracle Cards using Scryfall's current
  metadata endpoint. Both gzipped JSON Lines and legacy JSON arrays are supported.
- Bulk loading errors stop processing rather than triggering individual requests
  for every card. Individual lookup is only used for cards missing from a
  successfully loaded archive.
- Scryfall API might be slow or unreachable
- Unknown cards simply won't have images
- Ensure server has internet connection

### "No module named 'pandas'"

The virtual environment might not be activated:

```bash
source venv/bin/activate
```

---

## 📝 Technical Notes

- **D3.js v7**: Interactive force-directed graph visualization
- **Scryfall API**: Card image fetching (requires internet)
- **Python 3**: CSV data processing
- **No database**: Everything is static JSON

---

## 🎯 Future Improvements

- [ ] Cache card images locally
- [ ] Export layouts as images
- [ ] Search cards by name
- [ ] Additional real-time filters
- [ ] Multi-graph comparison
