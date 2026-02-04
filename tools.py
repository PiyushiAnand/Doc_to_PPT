# tools.py
from duckduckgo_search import DDGS
import requests

def search_web(query, max_results=3):
    """Fetches public market sentiment and business model info."""
    print(f"Searching web for: {query}...")
    results = DDGS().text(query, max_results=max_results)
    context_text = ""
    for r in results:
        context_text += f"Source ({r['title']}): {r['body']}\n"
    return context_text

def get_generic_image_url(query):
    """
    Finds a generic image (Placeholder logic).
    For production, integrate Pexels/Unsplash API.
    Requirement: Generic enough to not reveal identity[cite: 16].
    """
    # Using a placeholder service for stability in this example
    # In real submission, use: https://api.pexels.com/v1/search
    formatted_query = query.replace(" ", ",")
    return f"https://source.unsplash.com/800x600/?{formatted_query}"

def save_image(url, filename):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except:
        return None
    return None