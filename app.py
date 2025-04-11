from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import os
import json

# Load env variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

# 🔍 Subreddit matcher
def find_related_subreddits(query):
    with open("subreddits.json", "r") as f:
        subreddit_map = json.load(f)

    matched = set()
    query_lower = query.lower()

    for category, subs in subreddit_map.items():
        if category in query_lower:
            matched.update(subs)

    keyword_to_subs = {
        "headphones": ["HeadphoneAdvice", "audiophile"],
        "monitor": ["Monitors", "buildapc", "pcmasterrace"],
        "laptop": ["SuggestALaptop", "buildapc"],
        "budget": ["Frugal", "PersonalFinance"],
        "skincare": ["SkincareAddiction", "AsianBeauty"],
        "gaming": ["buildapc", "pcmasterrace", "GameDeals"]
    }

    for keyword, subs in keyword_to_subs.items():
        if keyword in query_lower:
            matched.update(subs)

    return list(matched)

# 🕵️ Real Reddit scraping via Google
def scrape_reddit_threads(query, subreddits, max_comments=5):
    print(f"🕵️ Scraping Reddit for query: {query}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_comments = []

    for sub in subreddits:
        search_query = f"{query} site:reddit.com/r/{sub}"
        google_url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}"
        print(f"🔎 Google search: {google_url}")

        try:
            html = requests.get(google_url, headers=headers).text
            soup = BeautifulSoup(html, 'html.parser')
            link_tags = soup.select('a')
            links = [a['href'].split('q=')[1].split('&')[0] for a in link_tags if '/url?q=' in a.get('href', '')]
            thread_links = [l for l in links if 'reddit.com/r/' in l]

            if thread_links:
                thread_url = thread_links[0]
                print(f"📎 Found thread: {thread_url}")
                thread_html = requests.get(thread_url, headers=headers).text
                thread_soup = BeautifulSoup(thread_html, 'html.parser')
                comment_tags = thread_soup.select('div[data-test-id="comment"]')
                comments = [tag.get_text().strip() for tag in comment_tags[:max_comments]]
                all_comments.extend(comments)

        except Exception as e:
            print(f"⚠️ Error scraping subreddit {sub}: {e}")

    return all_comments

@app.route('/')
def index():
    print("🧭 Loading index.html")
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q')
    print(f"🔍 User query: {query}")

    subreddits = find_related_subreddits(query)
    print(f"🎯 Matched subreddits: {subreddits}")

    comments = scrape_reddit_threads(query, subreddits)

    if not comments:
        comments = [f"No real comments found for '{query}', generating a fallback summary."]

    prompt = (
    "Based on the following Reddit comments, extract and RANK the top ten product recommendations. "
    "Include the product name, what it’s good for, and a brief explanation of why it’s popular. "
    "Ignore vague or spammy replies.\n\n"
    + "\n".join(comments)
)


    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        print("✅ AI Summary:", summary)

        return jsonify({'summary': summary, 'subreddits': subreddits})

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({'summary': "Oops! Something went wrong.", 'subreddits': subreddits})

if __name__ == '__main__':
    print("🚀 Trustie is live at http://localhost:5000")
    app.run(debug=True)
