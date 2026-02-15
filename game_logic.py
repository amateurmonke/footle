"""
game_logic.py - Core comparison and scoring logic for the Footle game.

All game rules live here, separated from the web layer.
"""

from __future__ import annotations
import hashlib
from datetime import date
from typing import Optional

import pandas as pd
from rapidfuzz import process, fuzz

from data_loader import PLAYERS_DF

# -- Position groups (for "close match" / yellow feedback) ---------------------
POSITION_GROUPS = {
    "GK":  "GK",
    "LB":  "DEF", "RB":  "DEF", "CB":  "DEF", "LWB": "DEF", "RWB": "DEF",
    "CDM": "MID", "CM":  "MID", "CAM": "MID", "LM":  "MID", "RM":  "MID",
    "LW":  "FWD", "RW":  "FWD", "LF":  "FWD", "RF":  "FWD",
    "ST":  "FWD", "CF":  "FWD",
}

MAX_GUESSES = 8

# -- Continent mapping (for "close match" / yellow nationality feedback) -------
NATIONALITY_TO_CONTINENT = {
    # Africa
    "Algeria": "Africa", "Burkina Faso": "Africa", "Cameroon": "Africa",
    "Congo DR": "Africa", "Côte d'Ivoire": "Africa", "Egypt": "Africa",
    "Gabon": "Africa", "Ghana": "Africa", "Guinea": "Africa",
    "Morocco": "Africa", "Nigeria": "Africa", "Senegal": "Africa",
    "Tunisia": "Africa",
    # South America
    "Argentina": "South America", "Brazil": "South America",
    "Colombia": "South America", "Ecuador": "South America",
    "Uruguay": "South America", "Venezuela": "South America",
    # North / Central America & Caribbean
    "Canada": "North America", "United States": "North America",
    # Europe
    "Armenia": "Europe", "Austria": "Europe", "Belgium": "Europe",
    "Bosnia and Herzegovina": "Europe", "Croatia": "Europe",
    "Czechia": "Europe", "Denmark": "Europe", "England": "Europe",
    "Finland": "Europe", "France": "Europe", "Georgia": "Europe",
    "Germany": "Europe", "Hungary": "Europe", "Italy": "Europe",
    "Kosovo": "Europe", "Netherlands": "Europe", "Norway": "Europe",
    "Poland": "Europe", "Portugal": "Europe", "Scotland": "Europe",
    "Serbia": "Europe", "Slovakia": "Europe", "Slovenia": "Europe",
    "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Türkiye": "Europe", "Ukraine": "Europe",
    # Asia
    "Japan": "Asia", "Korea Republic": "Asia",
    # Oceania
    "New Zealand": "Oceania",
}


def _get_continent(nationality: str) -> str:
    """Return the continent for a nationality, or 'Unknown'."""
    return NATIONALITY_TO_CONTINENT.get(nationality, "Unknown")


# -- Player lookup helpers -----------------------------------------------------

def search_players(query: str, limit: int = 8) -> list[dict]:
    """Return up to `limit` players whose name fuzzy-matches `query`.
    
    Used for the autocomplete endpoint.
    """
    if not query or len(query) < 2:
        return []

    query_lower = query.lower().strip()
    
    # Build choices list: (search_name, index)
    choices = PLAYERS_DF["search_name"].tolist()
    
    results = process.extract(
        query_lower, choices, scorer=fuzz.WRatio, limit=limit
    )
    
    players = []
    for match_name, score, idx in results:
        if score < 45:
            continue
        row = PLAYERS_DF.iloc[idx]
        players.append({
            "player_id": int(row["player_id"]),
            "short_name": row["short_name"],
            "long_name": row["long_name"],
            "club_name": row["club_name"],
            "player_face_url": row["player_face_url"],
            "score": score,
        })
    return players


def get_player_by_id(player_id: int) -> Optional[dict]:
    """Look up a single player by their EA player_id."""
    match = PLAYERS_DF[PLAYERS_DF["player_id"] == player_id]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


# -- Daily / random target selection ------------------------------------------

def get_daily_player_id() -> int:
    """Deterministic 'player of the day' based on the current UTC date.
    
    Uses a hash so the sequence isn't trivially predictable.
    Only selects players with overall rating > 85.
    """
    # Filter for players with rating > 85
    elite_players = PLAYERS_DF[PLAYERS_DF["overall"] >= 85]
    
    seed = hashlib.sha256(f"footle-{date.today().isoformat()}".encode()).hexdigest()
    index = int(seed, 16) % len(elite_players)
    return int(elite_players.iloc[index]["player_id"])


def get_random_player_id() -> int:
    """Pick a uniformly random player for 'random mode'."""
    row = PLAYERS_DF.sample(n=1).iloc[0]
    return int(row["player_id"])


# -- Comparison logic ---------------------------------------------------------

def _position_group(pos: str) -> str:
    """Map a specific position to its group (DEF / MID / FWD / GK)."""
    return POSITION_GROUPS.get(pos, "OTHER")


def compare(guess: dict, target: dict) -> dict:
    """Compare a guessed player to the target and return per-field feedback.

    Feedback values per field:
        "correct" = exact match   (green)
        "close"   = partial match (yellow)
        "wrong"   = no match      (red)

    For numeric fields (age, overall) an extra "direction" key is added:
        "higher"  = target value is higher than guess
        "lower"   = target value is lower than guess
        "equal"   = exact match
    """
    result: dict = {}

    # Nationality (exact = green, same continent = yellow, else red)
    g_nat = guess["nationality_name"]
    t_nat = target["nationality_name"]
    if g_nat == t_nat:
        nat_status = "correct"
    elif _get_continent(g_nat) == _get_continent(t_nat) and _get_continent(g_nat) != "Unknown":
        nat_status = "close"
    else:
        nat_status = "wrong"
    result["nationality"] = {"value": g_nat, "status": nat_status}

    # -- Club --------------------------------------------------------------
    result["club"] = {
        "value": guess["club_name"],
        "status": "correct" if guess["club_name"] == target["club_name"] else "wrong",
    }

    # -- League ------------------------------------------------------------
    result["league"] = {
        "value": guess["league_name"],
        "status": "correct" if guess["league_name"] == target["league_name"] else "wrong",
    }

    # Position (exact match = green, same group = yellow, else red)
    g_pos = guess["primary_position"]
    t_pos = target["primary_position"]
    if g_pos == t_pos:
        pos_status = "correct"
    elif _position_group(g_pos) == _position_group(t_pos):
        pos_status = "close"
    else:
        pos_status = "wrong"
    result["position"] = {"value": g_pos, "status": pos_status}

    # -- Age (numeric with direction) --------------------------------------
    g_age, t_age = int(guess["age"]), int(target["age"])
    if g_age == t_age:
        age_status, direction = "correct", "equal"
    else:
        age_status = "close" if abs(g_age - t_age) <= 2 else "wrong"
        direction = "higher" if t_age > g_age else "lower"
    result["age"] = {"value": g_age, "status": age_status, "direction": direction}

    # -- Overall (numeric with direction) ----------------------------------
    g_ovr, t_ovr = int(guess["overall"]), int(target["overall"])
    if g_ovr == t_ovr:
        ovr_status, direction = "correct", "equal"
    else:
        ovr_status = "close" if abs(g_ovr - t_ovr) <= 2 else "wrong"
        direction = "higher" if t_ovr > g_ovr else "lower"
    result["overall"] = {"value": g_ovr, "status": ovr_status, "direction": direction}

    # -- Radar stats (for the chart) ---------------------------------------
    stat_keys = ["pace", "shooting", "passing", "dribbling", "defending", "physic"]
    result["guess_stats"] = {k: int(guess[k]) for k in stat_keys}
    result["target_stats"] = {k: int(target[k]) for k in stat_keys}

    # -- Meta --------------------------------------------------------------
    result["guess_name"] = guess["short_name"]
    result["guess_face_url"] = guess.get("player_face_url", "")
    result["is_correct"] = (int(guess["player_id"]) == int(target["player_id"]))

    return result
