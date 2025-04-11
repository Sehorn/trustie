from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import requests
import os
import json

# Load environment variables
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

# 🔧 Reddit search + JSON comment scraping (upgraded!)
def scrape_reddit_threads(query, subreddits, max_threads=3, max_comments=10):
    print(f"🕵️ Scraping Reddit for: {query}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_comments = []

    for sub in subreddits:
        search_url = f"https://www.reddit.com/r/{sub}/search.json?q={requests.utils.quote(query)}&restrict_sr=1&sort=top&t=year"
        print(f"🔎 Searching: {search_url}")

        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code != 200:
                print(f"❌ Failed search on r/{sub}")
                continue

            posts = response.json().get('data', {}).get('children', [])
            if not posts:
                print(f"❌ No results in r/{sub}")
                continue

            for post in posts[:max_threads]:
                permalink = post['data'].get('permalink')
                thread_url = f"https://www.reddit.com{permalink}.json"
                print(f"📎 Fetching thread: {thread_url}")

                thread_response = requests.get(thread_url, headers=headers)
                if thread_response.status_code != 200:
                    print(f"❌ Failed to fetch thread JSON")
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

    print("✅ Total high-score comments scraped:", len(all_comments))
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
        comments = [f"No strong Reddit replies found for '{query}'. Here's a general summary instead."]

    prompt = (
        "Based on the following Reddit comments, extract and rank the top 5 product recommendations. "
        "Include the product name, what it’s good for, and a short reason why it's popular. "
        "Only use comments with helpful advice or personal experience.\n\n" + "\n".join(comments)
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
