from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

# Load .env and OpenAI key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

# 🔍 Find related subreddits based on user query
def find_related_subreddits(query):
    with open("subreddits.json", "r") as f:
        subreddit_map = json.load(f)

    matched = set()
    query_lower = query.lower()

    # Match by category name
    for category, subs in subreddit_map.items():
        if category in query_lower:
            matched.update(subs)

    # Fallback keyword matching
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

    # 🔄 Simulated placeholder text instead of real Reddit comments
    placeholder_comments = [
        f"User is searching for: '{query}'",
        f"Relevant subreddits: {', '.join(subreddits)}",
        "Trustie will fetch and summarize real comments from these communities soon."
    ]

    prompt = f"Summarize this information as if you were analyzing Reddit comments:\n{chr(10).join(placeholder_comments)}"

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
