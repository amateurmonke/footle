# Footle

A football player guessing game inspired by Wordle. Guess the hidden footballer in 8 tries using clues from each guess.

## How It Works

1. A mystery player is selected (daily challenge or random mode).
2. Type a player name and select from the autocomplete suggestions.
3. After each guess, colored feedback tells you how close you are:
   - **Green** - exact match
   - **Yellow** - close (same continent for nationality, same position group for position, within 2 for age/overall)
   - **Red** - wrong
   - Age and Overall show arrows (up/down) pointing toward the target.
4. Guess correctly within 8 tries to win!

## Dataset

Players rated 80+ overall from the top 5 European leagues (Premier League, La Liga, Bundesliga, Serie A, Ligue 1), sourced from EA FC 26.

## Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open [http://localhost:5111](http://localhost:5111) in your browser.

## Project Structure

```
footle/
  app.py              # Flask web server and API endpoints
  data_loader.py      # Loads cleaned CSV into memory at startup
  game_logic.py       # Comparison logic, scoring, fuzzy search
  requirements.txt    # Python dependencies
  data/
    footle_players.csv  # Cleaned player dataset (tracked in git)
    FC26_20250921.csv   # Raw EA FC dataset (not tracked)
  scripts/
    clean_data.py       # Script to regenerate footle_players.csv from raw data
  templates/
    index.html          # Single-page game UI
```

## Regenerating the Dataset

If you update the raw CSV, re-run the cleaning script:

```bash
python scripts/clean_data.py
```

## Features

- Daily challenge mode (same player for everyone each day)
- Random mode
- Fuzzy autocomplete player search
- Color-coded guess history table
- Nationality feedback with continent-based "close" matching
- Radar chart comparing guess stats vs target
- Confetti celebration on win
