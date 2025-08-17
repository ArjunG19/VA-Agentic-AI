from mcp.server.fastmcp import FastMCP
from typing import Optional
import logging
import requests
import redis
from redis.commands.search.query import Query
import urllib.parse

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="VA", port=8000)

@mcp.tool()
def play_movie(keywords: str, platform_name: str) -> str:
    """
    Play a movie on the specified video streaming platform. If any parameter is missing ask the user for it one by one. Do not assume anything on your own

    Args:
        movie_name (str): Keywords given by the user for the movie like title, genre, actor, director, etc.
        platform_name (str): Must be one of: Netflix, Hulu, Disney+, Amazon Prime, HBO Max, YouTube, Apple TV+.

    Returns:
        str: Confirmation message with matched movie (and rating if available), 
             or validation/suggestion message with other movie recommendations.
    """
    allowed_platforms = ['Netflix', 'Hulu', 'Disney+', 'Amazon Prime', 'HBO Max', 'YouTube', 'Apple TV+']
    if platform_name not in allowed_platforms:
        return f"Invalid platform. Available platforms: {', '.join(allowed_platforms)}"
    
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    query = Query(f"@search_text:{keywords}").paging(0, 1)
    results = r.ft("movies").search(query)
    
    if not results.docs:
        return "No matching movies found"
    
    result= ", ".join(doc.title for doc in results.docs)
    response = f"Playing '{result}' on {platform_name}"
    return response

@mcp.tool()
def play_music(keywords: str) -> str:
    """
    Play a song using Jio Saavn given any details like song name, artist name, album name, genre.

    Args:
        keywords (str): The search text describing what the user is looking for. Can include keywords from the track name, artist names, album name, or genre.

    Returns:
        str: matched songs
    """
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    
    # Search by matching query in the search_text field
    query = Query(f"@search_text:{keywords}").paging(0, 1)
    results = r.ft("tracks").search(query)
    
    if not results.docs:
        return "No matching songs found."
    
    # Convert to readable string format
    output_str = "\n".join(f"{doc.track_name} by {doc.artists}" for doc in results.docs)
    return output_str

@mcp.tool()
def play_game(keywords: str) -> str:
    """
    Launch a game using Jio Games service. 

    Args:
        game_name (str): Name or partial name of the game to launch or genre or publisher.

    Returns:
        str: Confirmation message with matched game (plus rating/year if available) or prompts user if input is missing.
    """
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    query = Query(f"@search_text:{keywords}").paging(0, 1)
    results = r.ft("games").search(query)
    if not results.docs:
        return "No matching games found."
    return ", ".join(doc.Name for doc in results.docs)

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

api_key = "api_key"
@mcp.tool()
def get_weather_by_location_name(place_name):
    """
    Get current weather data for a location by name.

    Args:
        place_name (str): Name of the place (city, address, landmark, etc.).

    Returns:
        dict:
            Dictionary with important weather details, including:
                - location: The place name used
                - temperature_celsius: Current temperature in °C
                - condition: Weather description (e.g., "Partly sunny")
                - humidity_percent: Relative humidity (%)
                - wind_speed_kmh: Wind speed (km/h)
                - wind_direction: Wind direction (cardinal)
                - precipitation_probability_percent: Chance of rain (%)
                - uv_index: Ultraviolet index
                - time_zone: Time zone ID for the location
            On error or if no data is found, returns an error dictionary.
    """
    # Step 1: Get coordinates from location name
    encoded_place = urllib.parse.quote(place_name)
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_place}&key={api_key}"
    geo_resp = requests.get(geocode_url)
    if geo_resp.status_code != 200:
        return {"error": geo_resp.status_code, "msg": geo_resp.text}
    geo_data = geo_resp.json()
    if not geo_data.get("results"):
        return {"error": "No results from Geocoding API"}
    location = geo_data["results"][0]["geometry"]["location"]
    lat, lon = location["lat"], location["lng"]

    # Step 2: Get current weather
    base = "https://weather.googleapis.com/v1/"
    wurl = f"{base}currentConditions:lookup?key={api_key}&location.latitude={lat}&location.longitude={lon}"
    resp = requests.get(wurl)
    if resp.status_code != 200:
        return {"error": resp.status_code, "msg": resp.text}
    wdata = resp.json()

    # Step 3: Extract important current weather data
    cond = wdata.get('weatherCondition', {})
    result = {
        'location': place_name,
        'temperature_celsius': wdata.get('temperature', {}).get('degrees'),
        'condition': cond.get('description', {}).get('text'),
        'humidity_percent': wdata.get('relativeHumidity'),
        'wind_speed_kmh': wdata.get('wind', {}).get('speed', {}).get('value'),
        'wind_direction': wdata.get('wind', {}).get('direction', {}).get('cardinal'),
        'precipitation_probability_percent': wdata.get('precipitation', {}).get('probability', {}).get('percent'),
        'uv_index': wdata.get('uvIndex'),
        'time_zone': wdata.get('timeZone', {}).get('id')
    }
    return result


if __name__ == "__main__":
    logger.info("Starting Virtual Assistant MCP Server...")
    try:
        mcp.run("sse")
    except Exception as e:
        logger.error(f"Server startup error: {e}")
        raise
