# import requests

# API_KEY = "AIzaSyCgr04v36qJDCLpmpuTBDgAgQuHOqmnEOQ"
# SEARCH_ENGINE_ID = "715bfed6b2f6a407f"

# # Firqa-related sites
# FIRQA_SITES = {
#     "barelvi": "site:thefatwa.com OR site:daruliftaahlesunnat.net OR site:daruliftabareilly.com",
#     "deobandi": "site:darulifta-deoband.com OR site:banuri.edu.pk OR site:darulifta-deoband.com/en",
#     "ahlehadith": "site:ahlelhadith.com OR site:forum.mohaddis.com",
# }

# def search_google(query, firqa_sites=""):
#     """Google Custom Search API se request bhejne ka function."""
#     base_url = "https://www.googleapis.com/customsearch/v1"

#     params = {
#         "q": f"{query} {firqa_sites}" if firqa_sites else query,
#         "key": API_KEY,
#         "cx": SEARCH_ENGINE_ID,
#         "num": 6,
#     }

#     try:
#         response = requests.get(base_url, params=params)
#         response.raise_for_status()
#         data = response.json()

#         return data.get("items", [])
#     except requests.exceptions.RequestException as e:
#         print(f"Request failed: {e}")
#         return []

# def main():
#     query = input("Enter search query: ").strip()
#     firqa = input("Enter firqa (barelvi/deobandi/ahlehadith or leave empty for all): ").strip().lower()

#     results = {}

#     if firqa and firqa in FIRQA_SITES:
#         results[firqa] = search_google(query, FIRQA_SITES[firqa])
#     elif firqa == "":
#         combined_sites = " OR ".join(FIRQA_SITES.values())
#         results["all"] = search_google(query, combined_sites)

#     # Output structured format
#     print("\n--- Search Results ---\n")
#     for category, items in results.items():
#         print(f"Results for: {category.upper()}\n")
#         for idx, item in enumerate(items, start=1):
#             print(f"{idx}. {item.get('title')}\n   {item.get('link')}\n   {item.get('snippet')}\n")
#         print("-" * 50)

# if __name__ == "__main__":
#     main()



from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Load API key and Search Engine ID from environment variables
API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

# Define websites for different sects (FIRQA_SITES)
FIRQA_SITES = {
    "barelvi": "site:thefatwa.com OR site:daruliftaahlesunnat.net OR site:daruliftabareilly.com",
    "deobandi": "site:darulifta-deoband.com OR site:banuri.edu.pk OR site:darulifta-deoband.com/en",
    "ahlehadith": "site:ahlelhadith.com OR site:forum.mohaddis.com",
}

def search_google(query, firqa_sites=""):
    """Search Google Custom Search API."""
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{query} {firqa_sites}" if firqa_sites else query,
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "num": 6,
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route("/search", methods=["GET"])
def search():
    """Handle search queries with optional sect filter."""
    query = request.args.get("query", "").strip()
    firqa = request.args.get("firqa", "").strip().lower()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    results = {}
    if firqa and firqa in FIRQA_SITES:
        results[firqa] = search_google(query, FIRQA_SITES[firqa])
    else:
        combined_sites = " OR ".join(FIRQA_SITES.values())
        results["all"] = search_google(query, combined_sites)
    
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway dynamically assigns a port
    app.run(host="0.0.0.0", port=port, debug=True)
