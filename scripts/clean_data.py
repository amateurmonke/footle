"""
Clean the raw EA FC CSV dataset for the Footle game.

Filters:
  - Only players rated 80+ overall
  - Only players from the top 5 European leagues:
    Premier League, La Liga, Bundesliga, Serie A, Ligue 1

Outputs:
  - footle_players.csv  (cleaned dataset with only game-relevant columns)
"""
import pandas as pd
import unicodedata
import re
import os

# Resolve paths relative to the project root (one level up from scripts/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RAW_CSV = os.path.join(_PROJECT_ROOT, "data", "FC26_20250921.csv")
_OUTPUT_CSV = os.path.join(_PROJECT_ROOT, "data", "footle_players.csv")

# -- 1. Load raw data ----------------------------------------------------------
raw = pd.read_csv(_RAW_CSV)
print(f'Raw dataset: {raw.shape[0]} players, {raw.shape[1]} columns')

# -- 2. Filter: top 5 European leagues only ------------------------------------
TOP_5_LEAGUES = [
    'Premier League',
    'La Liga',
    'Bundesliga',
    'Serie A',
    'Ligue 1',
]
df = raw[raw['league_name'].isin(TOP_5_LEAGUES)].copy()
print(f'After league filter (top 5): {len(df)} players')

# -- 3. Filter: overall rating 80+ ---------------------------------------------
df = df[df['overall'] >= 80].copy()
print(f'After overall >= 80 filter: {len(df)} players')

# -- 4. Select only the columns the game needs ---------------------------------
GAME_COLUMNS = [
    'player_id',
    'short_name',
    'long_name',
    'player_positions',   # e.g. "CAM, CM"
    'overall',
    'age',
    'club_name',
    'league_name',
    'nationality_name',
    'player_face_url',
    # Radar-chart stats (six main attributes)
    'pace',
    'shooting',
    'passing',
    'dribbling',
    'defending',
    'physic',
]
df = df[GAME_COLUMNS].copy()

# -- 5. Clean player names -----------------------------------------------------
# Normalise unicode (e.g. accented characters) to NFC form so fuzzy matching
# works consistently, but keep the accented display name intact.

def clean_name(name: str) -> str:
    """Strip Arabic/non-Latin script appended to some names and normalise unicode."""
    if pd.isna(name):
        return name
    # Some long_names have Arabic script glued on (e.g. "Achraf Hakimi Mouhأشرف حكيمي")
    # Keep only Latin-script characters, spaces, hyphens, apostrophes, and periods.
    cleaned = re.sub(r'[^\u0000-\u024F\u1E00-\u1EFF\s\'\-\.]', '', name)
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Normalise unicode to NFC
    cleaned = unicodedata.normalize('NFC', cleaned)
    return cleaned

df['long_name'] = df['long_name'].apply(clean_name)
df['short_name'] = df['short_name'].apply(clean_name)

# -- 6. Create a search-friendly name (ASCII, lowercase) for fuzzy matching ---
def to_search_name(name: str) -> str:
    """Convert to lowercase ASCII for search/matching purposes."""
    if pd.isna(name):
        return ''
    # Decompose unicode, strip combining marks (accents), recompose
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().strip()

df['search_name'] = df['long_name'].apply(to_search_name)

# -- 7. Normalise positions: take the primary (first listed) position ----------
df['primary_position'] = df['player_positions'].apply(
    lambda x: x.split(',')[0].strip() if pd.notna(x) else 'Unknown'
)

# -- 8. Drop rows with critical missing data ----------------------------------
critical_cols = ['short_name', 'long_name', 'club_name', 'league_name',
                 'nationality_name', 'overall', 'age']
before = len(df)
df = df.dropna(subset=critical_cols)
dropped = before - len(df)
if dropped:
    print(f'Dropped {dropped} rows with missing critical data')

# -- 9. Drop duplicate player_ids (keep first occurrence) ----------------------
dupes = df['player_id'].duplicated().sum()
if dupes:
    print(f'Dropping {dupes} duplicate player_id rows')
    df = df.drop_duplicates(subset='player_id', keep='first')

# -- 10. Reset index -----------------------------------------------------------
df = df.reset_index(drop=True)

# -- 11. Summary stats ---------------------------------------------------------
print()
print('=' * 60)
print(f'CLEANED DATASET: {len(df)} players')
print(f'  Leagues:       {df["league_name"].nunique()} -> {sorted(df["league_name"].unique())}')
print(f'  Clubs:         {df["club_name"].nunique()}')
print(f'  Nationalities: {df["nationality_name"].nunique()}')
print(f'  Overall range: {df["overall"].min()} - {df["overall"].max()}')
print(f'  Age range:     {df["age"].min()} - {df["age"].max()}')
print(f'  Positions:     {sorted(df["primary_position"].unique())}')
print()
print('League breakdown:')
print(df['league_name'].value_counts().to_string())
print()
print('Sample rows:')
print(df[['short_name', 'long_name', 'club_name', 'league_name',
          'nationality_name', 'overall', 'age', 'primary_position']].head(15).to_string())

# -- 12. Save cleaned CSV -----------------------------------------------------
df.to_csv(_OUTPUT_CSV, index=False)
print(f'\nSaved cleaned dataset to {_OUTPUT_CSV} ({len(df)} players)')
