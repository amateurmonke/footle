"""
app.py - Flask web server for the Footle game.

Endpoints:
    GET  /                  - Serve the main game page
    GET  /api/autocomplete  - Fuzzy player name search
    POST /api/new_game      - Start a new game (daily or random)
    POST /api/guess         - Submit a guess and receive comparison feedback
"""

from flask import Flask, render_template, request, jsonify, session
import os

from game_logic import (
    search_players,
    get_player_by_id,
    get_daily_player_id,
    get_random_player_id,
    compare,
    MAX_GUESSES,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "footle-dev-secret-key-change-me")


# -- Pages ---------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the single-page game UI."""
    return render_template("index.html")


# -- API: Autocomplete --------------------------------------------------------

@app.route("/api/autocomplete")
def autocomplete():
    """Return fuzzy-matched player names for the search box."""
    query = request.args.get("q", "").strip()
    results = search_players(query, limit=8)
    return jsonify(results)


# -- API: New Game -------------------------------------------------------------

@app.route("/api/new_game", methods=["POST"])
def new_game():
    """Start a new game session. Body JSON: { "mode": "daily" | "random" }"""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "daily")

    if mode == "daily":
        target_id = get_daily_player_id()
    else:
        target_id = get_random_player_id()

    # Store game state in the server-side session
    session["target_id"] = target_id
    session["guesses"] = []
    session["mode"] = mode
    session["game_over"] = False
    session["won"] = False

    return jsonify({
        "status": "ok",
        "mode": mode,
        "max_guesses": MAX_GUESSES,
    })


# -- API: Submit a Guess ------------------------------------------------------

@app.route("/api/guess", methods=["POST"])
def guess():
    """Process a player guess. Body JSON: { "player_id": 12345 }"""
    # Validate session
    if "target_id" not in session:
        return jsonify({"error": "No active game. Start a new game first."}), 400

    if session.get("game_over"):
        target = get_player_by_id(session["target_id"])
        return jsonify({
            "error": "Game is already over.",
            "game_over": True,
            "won": session.get("won", False),
            "target": _player_summary(target) if target else None,
        }), 400

    data = request.get_json(silent=True) or {}
    player_id = data.get("player_id")
    if player_id is None:
        return jsonify({"error": "Missing player_id."}), 400

    # Look up both players
    guess_player = get_player_by_id(int(player_id))
    if guess_player is None:
        return jsonify({"error": "Player not found."}), 404

    target_player = get_player_by_id(session["target_id"])
    if target_player is None:
        return jsonify({"error": "Internal error: target player missing."}), 500

    # Prevent duplicate guesses
    past_ids = session.get("guesses", [])
    if int(player_id) in past_ids:
        return jsonify({"error": "You already guessed this player."}), 400

    # Run comparison
    feedback = compare(guess_player, target_player)

    # Update session state
    past_ids.append(int(player_id))
    session["guesses"] = past_ids

    game_over = False
    won = False
    if feedback["is_correct"]:
        game_over = True
        won = True
    elif len(past_ids) >= MAX_GUESSES:
        game_over = True
        won = False

    session["game_over"] = game_over
    session["won"] = won

    response = {
        "feedback": feedback,
        "guess_number": len(past_ids),
        "max_guesses": MAX_GUESSES,
        "game_over": game_over,
        "won": won,
    }

    # If game over, reveal the target
    if game_over:
        response["target"] = _player_summary(target_player)

    return jsonify(response)


def _player_summary(player: dict) -> dict:
    """Return a safe subset of player data for the client."""
    return {
        "player_id": int(player["player_id"]),
        "short_name": player["short_name"],
        "long_name": player["long_name"],
        "club_name": player["club_name"],
        "league_name": player["league_name"],
        "nationality_name": player["nationality_name"],
        "age": int(player["age"]),
        "overall": int(player["overall"]),
        "primary_position": player["primary_position"],
        "player_face_url": player.get("player_face_url", ""),
        "pace": int(player.get("pace", 0)),
        "shooting": int(player.get("shooting", 0)),
        "passing": int(player.get("passing", 0)),
        "dribbling": int(player.get("dribbling", 0)),
        "defending": int(player.get("defending", 0)),
        "physic": int(player.get("physic", 0)),
    }


# -- Run -----------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5111)
