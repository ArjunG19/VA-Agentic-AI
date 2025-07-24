import argparse
from ast import arg
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="demo ",port=8000)

@mcp.tool()
def play_movie(movie_name: str, platform_name: str) -> str:
    """
    Play a movie on the user's device on the specified platform. If no movie name is provided, ask the user for the movie name. If no platform is provided, ask the user for the platform.

    Args:
        movie_name: The name of the movie to play.
        platform_name: The platform to play the movie on. Must be one of: ['Netflix', 'Hulu', 'Disney+', 'Amazon Prime', 'HBO Max']

    Returns:
        A message indicating that the movie is playing.
    """
    allowed_platforms = ['Netflix', 'Hulu', 'Disney+', 'Amazon Prime', 'HBO Max']
    if platform_name not in allowed_platforms:
        raise ValueError(f"Invalid platform. Choose from: {', '.join(allowed_platforms)}")

    return f"Playing '{movie_name}' on {platform_name}"

@mcp.tool()
def play_music(song_name: str) -> str:
    """
    Play a song on the user's device using Jio Saavn. If no song name is provided, ask the user for the song name.

    Args:
        song_name: The name of the song to play.
        
    Returns:
        A message indicating that the song is playing.
    """
    return f"Playing '{song_name}' on Jio Saavn"

if __name__ == "__main__":
    print("Starting server")
    parser=argparse.ArgumentParser()
    parser.add_argument(
        "--server_type",type=str,default="sse",choices=["sse","stdio"]
    )
    args=parser.parse_args()
    mcp.run(args.server_type)
    print("MCP server is running.")