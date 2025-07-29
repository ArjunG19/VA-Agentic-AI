from mcp.server.fastmcp import FastMCP
import sqlite3
from rapidfuzz import process, fuzz
from typing import Optional
import os
import logging

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="VA", port=8000)

def get_db_connection():
    """
    Get a SQLite database connection to 'media.db'. 
    Handles file existence and connection errors gracefully.

    Returns:
        sqlite3.Connection or None: Returns connection object if successful, else None.
    """
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'media.db')
        if not os.path.exists(db_path):
            logger.warning(f"Database not found at {db_path}")
            return None
        return sqlite3.connect(db_path, check_same_thread=False)
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def fuzzy_search(query: str, entity_type: str, threshold: float = 70) -> dict:
    """
    Perform a fuzzy search for movies, games, or songs in the media database.

    Args:
        query (str): The search term.
        entity_type (str): One of {'movies', 'games', 'songs'}.
        threshold (float, optional): Minimum required confidence (0-100) for a positive match.

    Returns:
        dict: A dictionary with fields:
            - title (str): Matched title or error message.
            - poster (str or None): Poster URL/path if available.
            - suggestions (list): Up to 2 alternative matches (title and score).
            - rating (str, optional): Rating info if present.
            - year (str/int, optional): Year info if present.
    """
    logger.info(f"Searching for {entity_type}: '{query}'")
    
    if not query or query.lower() == "not specified":
        return {
            "title": "Not specified (no clear match found)", 
            "poster": None,
            "suggestions": []
        }
    
    conn = get_db_connection()
    if not conn:
        return {
            "title": "Not specified (database unavailable)", 
            "poster": None,
            "suggestions": []
        }
    
    try:
        cursor = conn.cursor()
        table_map = {"movies": "movies", "games": "games", "songs": "songs"}
        
        if entity_type not in table_map:
            return {
                "title": "Not specified (invalid entity type)", 
                "poster": None,
                "suggestions": []
            }
        
        cursor.execute(f"PRAGMA table_info({table_map[entity_type]})")
        columns = [col[1] for col in cursor.fetchall()]
        select_fields = ["title"]
        if "poster" in columns:
            select_fields.append("poster")
        if "rating" in columns:
            select_fields.append("rating")
        if "year" in columns:
            select_fields.append("year")
        
        query_sql = f"SELECT {', '.join(select_fields)} FROM {table_map[entity_type]}"
        cursor.execute(query_sql)
        database = cursor.fetchall()
        if not database:
            return {
                "title": "Not specified (no entries found)", 
                "poster": None,
                "suggestions": []
            }
        
        titles = [row[0] for row in database]
        normalized_query = query.lower()
        matches = process.extract(normalized_query, titles, scorer=fuzz.ratio, limit=3)
        if not matches:
            return {
                "title": "Not specified (no match found)", 
                "poster": None,
                "suggestions": []
            }
        
        best_match, best_score, best_index = matches[0]
        best_row = database[best_index]
        result = {
            "title": best_row[0],
            "poster": best_row[1] if len(best_row) > 1 else None,
            "suggestions": []
        }
        if len(best_row) > 2 and best_row[2]:
            result["rating"] = best_row[2]
        if len(best_row) > 3 and best_row[3]:
            result["year"] = best_row[3]
        for match, score, index in matches[1:]:
            if score >= 50:
                result["suggestions"].append({
                    "title": database[index][0],
                    "score": score
                })
        if best_score >= threshold:
            logger.info(f"Found match: {result['title']} (score: {best_score})")
            return result
        else:
            logger.info(f"Low confidence match: {result['title']} (score: {best_score})")
            return {
                "title": f"Not specified (did you mean '{result['title']}'?)",
                "poster": None,
                "suggestions": result["suggestions"]
            }
            
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        return {
            "title": "Not specified (database error)", 
            "poster": None,
            "suggestions": []
        }
    finally:
        conn.close()

@mcp.tool()
def play_movie(movie_name: str, platform_name: str) -> str:
    """
    Play a movie on the specified video streaming platform. If any parameter is missing ask the user for it one by one. Do not assume anything on your own

    Args:
        movie_name (str): Name or partial name of the movie to play.
        platform_name (str): Must be one of: Netflix, Hulu, Disney+, Amazon Prime, HBO Max, YouTube, Apple TV+.

    Returns:
        str: Confirmation message with matched movie (and rating if available), 
             or validation/suggestion message with other movie recommendations.
    """
    allowed_platforms = ['Netflix', 'Hulu', 'Disney+', 'Amazon Prime', 'HBO Max', 'YouTube', 'Apple TV+']
    if platform_name not in allowed_platforms:
        return f"Invalid platform. Available platforms: {', '.join(allowed_platforms)}"
    
    result = fuzzy_search(movie_name, "movies")
    response = f"Playing '{result['title']}' on {platform_name}"
    if result.get('rating'):
        response += f" (Rating: {result['rating']})"
    if result.get('suggestions') and "did you mean" in result['title']:
        suggestions = [s['title'] for s in result['suggestions'][:2]]
        response += f"\n\nOther options: {', '.join(suggestions)}"
    return response

@mcp.tool()
def play_music(song_name: str) -> str:
    """
    Play a song using Jio Saavn. If the song name is missing ask the user for it.

    Args:
        song_name (str): Name or partial name of the song to play.

    Returns:
        str: Confirmation message with matched song; prompts user if song name is not provided.
    """
    if not song_name or not song_name.strip():
        return "Please provide a song name to play."
    result = fuzzy_search(song_name, "songs")
    song_title = result['title'] if result['title'] != "Not specified (no entries found)" else song_name
    return f"Playing '{song_title}' on Jio Saavn"

@mcp.tool()
def play_game(game_name: str) -> str:
    """
    Launch a game using Jio Games service. If the name of the game is missing ask the user fro it.

    Args:
        game_name (str): Name or partial name of the game to launch.

    Returns:
        str: Confirmation message with matched game (plus rating/year if available) or prompts user if input is missing.
    """
    if not game_name or not game_name.strip():
        return "Please provide a game name to play."
    result = fuzzy_search(game_name, "games")
    response = f"Launching '{result['title']}' on Jio Games"
    if result.get('rating'):
        response += f" (Rating: {result['rating']})"
    if result.get('year'):
        response += f" ({result['year']})"
    return response

@mcp.tool()
def install_app(app_name: str) -> str:
    """
    Install an application from the Jio Store. If the app name is missing ask the user for it.

    Args:
        app_name (str): Name of the app to install (must not be empty).

    Returns:
        str: Confirmation message including app category if detected; prompts user if name is missing.
    """
    if not app_name or not app_name.strip():
        return "Please provide an app name to install."
    app_categories = {
        'social': ['whatsapp', 'facebook', 'instagram', 'twitter', 'snapchat'],
        'productivity': ['office', 'docs', 'notion', 'slack', 'zoom'],
        'entertainment': ['spotify', 'youtube', 'netflix', 'tiktok'],
        'utility': ['calculator', 'calendar', 'weather', 'maps']
    }
    category = None
    app_lower = app_name.lower()
    for cat, apps in app_categories.items():
        if any(app in app_lower for app in apps):
            category = cat.title()
            break
    response = f"Installing '{app_name}' from Jio Store. The app will be available on your device shortly."
    if category:
        response += f" (Category: {category})"
    return response

@mcp.tool()
def control_volume(action: str, value: Optional[int] = None) -> str:
    """
    Control the system volume.

    Args:
        action (str): One of {'increase', 'decrease', 'mute', 'unmute', 'set'}. 
        value (int, optional): Amount (%) to adjust or set volume (for applicable actions).

    Returns:
        str: Message reflecting volume control or guidance if usage is incorrect.
    """
    action = action.lower().strip()
    allowed_actions = ['increase', 'decrease', 'mute', 'unmute', 'set']
    if action not in allowed_actions:
        return f"Invalid action. Please use one of: {', '.join(allowed_actions)}"
    if action == 'mute':
        return "Volume muted"
    elif action == 'unmute':
        return "Volume unmuted"
    elif action == 'increase':
        amount = value if value is not None else 10
        if not 1 <= amount <= 100:
            return "Volume increase amount must be between 1 and 100"
        return f"Volume increased by {amount}%"
    elif action == 'decrease':
        amount = value if value is not None else 10
        if not 1 <= amount <= 100:
            return "Volume decrease amount must be between 1 and 100"
        return f"Volume decreased by {amount}%"
    elif action == 'set':
        if value is None:
            return "Please provide a volume level (0-100) when setting volume"
        if not 0 <= value <= 100:
            return "Volume level must be between 0 and 100"
        return f"Volume set to {value}%"

@mcp.tool()
def get_system_info() -> str:
    """
    Get high-level system and service information.

    Returns:
        str: Information about simulated current volume, available services, app store, and database status.
    """
    conn = get_db_connection()
    db_status = "Connected" if conn else "Not available"
    if conn:
        conn.close()
    return (
        f"System Information:\n"
        f"- Current Volume: 75% (simulated)\n"
        f"- Available Platforms: Netflix, Hulu, Disney+, Amazon Prime, HBO Max, YouTube, Apple TV+\n"
        f"- Music Service: Jio Saavn\n"
        f"- Gaming Service: Jio Games\n"
        f"- App Store: Jio Store\n"
        f"- Media Database: {db_status}\n"
        f"- Fuzzy Search: Enabled (70% threshold)\n"
    )

if __name__ == "__main__":
    logger.info("Starting Virtual Assistant MCP Server...")
    try:
        mcp.run("sse")
    except Exception as e:
        logger.error(f"Server startup error: {e}")
        raise
