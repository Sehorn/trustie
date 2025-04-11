from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import requests
import os
import json
import ast
import re


# Load .env and OpenAI key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

# 🔍 Curated subreddit matcher
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

# 🔮 GPT-powered subreddit suggestions

def gpt_suggest_subreddits(query):
    prompt = f"""
Only return a Python list of subreddit names for: "{query}".
No explanations, no intro, no formatting, no extra characters.
The list should look like: ['example1', 'example2']
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        print("🧠 GPT Suggested Subreddits:", raw)

        try:
            suggested = ast.literal_eval(raw)
        except Exception:
            match = re.search(r"\[.*\]", raw)
            if match:
                try:
                    suggested = ast.literal_eval(match.group())
                except Exception:
                    suggested = []
            else:
                suggested = []

        return [s.strip().replace("r/", "") for s in suggested if isinstance(s, str)]

    except Exception as e:
        print("❌ GPT subreddit fetch failed:", e)
        return []

# 🕸️ Scrape comments from top threads in subreddits
def scrape_reddit_threads(query, subreddits, max_threads=3, max_comments=10):
    print(f"🕵️ Scraping Reddit for: {query}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_comments = []

    for sub in subreddits:
        search_url = f"https://www.reddit.com/r/{sub}/search.json?q={requests.utils.quote(query)}&restrict_sr=1&sort=top&t=year"
        print(f"🔎 Searching: {search_url}")

        try:
            response = requests.get(search_url, headers=headers)
            posts = response.json().get('data', {}).get('children', [])
            if not posts:
                print(f"❌ No results in r/{sub}")
                continue

            for post in posts[:max_threads]:
                title = post['data'].get('title', '').lower()
                if not any(word in title for word in query.lower().split()):
                    continue

                permalink = post['data'].get('permalink')
                thread_url = f"https://www.reddit.com{permalink}.json"
                print(f"📎 Thread: {thread_url}")

                thread_response = requests.get(thread_url, headers=headers)
                if thread_response.status_code != 200:
                    continue

                comments_data = thread_response.json()[1]['data']['children']
                scored_comments = []

                for c in comments_data:
                    if c['kind'] != 't1':
                        continue
                    body = c['data'].get('body')
                    score = c['data'].get('score', 0)
                    if body and score >= 5:
                        scored_comments.append((score, body.strip()))

                top_comments = sorted(scored_comments, reverse=True)[:max_comments]
                all_comments.extend([body for score, body in top_comments])

        except Exception as e:
            print(f"⚠️ Error scraping r/{sub}: {e}")

    print("✅ Total good comments:", len(all_comments))
    return all_comments

@app.route('/')
def index():
    print("🧭 Loading index.html")
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q')
    print(f"🔍 User query: {query}")

    mapped_subs = find_related_subreddits(query)
    gpt_subs = gpt_suggest_subreddits(query)
    subreddits = list(set(mapped_subs + gpt_subs))
    print(f"📚 Final subreddit list: {subreddits}")

    comments = scrape_reddit_threads(query, subreddits)

    if not comments:
        comments = [f"No strong Reddit replies found for '{query}'. Here's a general summary instead."]

    prompt = (
    f"Summarize these Reddit comments into 3-5 specific product recommendations for '{query}'. "
    "Return them as plain text bullet points, each starting with a dash. "
    "Each bullet should include the product name, what it’s good for, and why it's recommended.\n\n"
    + "\n".join(comments)
)

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        print("✅ AI Summary:", summary)

        return jsonify({'summary': summary, 'subreddits': subreddits})

    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({'summary': "Oops! Something went wrong.", 'subreddits': subreddits})

if __name__ == '__main__':
    print("🚀 Trustie is running at http://localhost:5000")
    app.run(debug=True)
