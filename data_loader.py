"""
data_loader.py - Load and prepare the cleaned Footle player dataset.

Reads data/footle_players.csv into a pandas DataFrame at import time so it
stays in memory for the lifetime of the server process.
"""

import os
import pandas as pd

# Path to the cleaned CSV (lives in the data/ directory)
_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "footle_players.csv")


def load_players() -> pd.DataFrame:
    """Read the cleaned CSV and return a ready-to-use DataFrame."""
    df = pd.read_csv(_CSV_PATH)

    # Ensure numeric columns are the right type
    numeric_cols = ["overall", "age", "pace", "shooting", "passing",
                    "dribbling", "defending", "physic"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill any remaining NaN in stat columns with 0 (e.g. GK pace)
    stat_cols = ["pace", "shooting", "passing", "dribbling", "defending", "physic"]
    df[stat_cols] = df[stat_cols].fillna(0).astype(int)

    # Make sure search_name exists and is lowercase
    if "search_name" not in df.columns:
        import unicodedata
        df["search_name"] = df["long_name"].apply(
            lambda n: "".join(
                c for c in unicodedata.normalize("NFKD", str(n))
                if not unicodedata.combining(c)
            ).lower().strip()
        )

    return df


# Pre-load once at module level
PLAYERS_DF = load_players()
