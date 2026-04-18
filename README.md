# mtglogit
Run analysis of mtg limited decks using logistic regression

# Analysis
/home/tarrago/git/mtglogit/.venv/bin/python main.py --min-pair-freq 0.0005 --data-dir /home/tarrago/git/mtglogit/data/game_data_public.Cube_-_Powered.PremierDraft.csv

# Postprocessing 
cd view && python3 wrinfo.py

cd view && python -m http.server
