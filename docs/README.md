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

- **Dataset**: Switch which data is visualized
- **Link Visible Threshold** (1.0 - 2.0): Link visibility sensitivity
- **SELF_PROB High** (1.0 - 1.5): Threshold for green glow
- **SELF_PROB Low** (0.5 - 1.0): Threshold for red glow

Press **Apply** to reload with new parameters.

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
