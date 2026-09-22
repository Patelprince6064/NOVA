"""Website aliases for Nova browser control — safe allowlist."""

# Keep in sync with pc/controller WEBSITE_ALIASES but canonical is here.
WEBSITE_ALIASES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "linkedin": "https://www.linkedin.com",
    "chatgpt": "https://chat.openai.com",
}

# Helper for Google search URL
def google_search_url(query: str) -> str:
    import urllib.parse
    q = urllib.parse.quote_plus(query.strip())
    return f"https://www.google.com/search?q={q}"

def youtube_search_url(query: str) -> str:
    import urllib.parse
    q = urllib.parse.quote_plus(query.strip())
    return f"https://www.youtube.com/results?search_query={q}"
