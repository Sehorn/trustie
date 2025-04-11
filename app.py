from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

# ✅ Load the .env first
load_dotenv()

# ✅ Now you can safely fetch the key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q')

    # Simulated Reddit comments
    comments = [
        "The Sony WH-1000XM5 are amazing for noise cancelling and battery life.",
        "I really like the Bose QC45, super comfortable and solid sound quality."
    ]

    prompt = f"Summarize these Reddit comments into the top product recommendations:\n{chr(10).join(comments)}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        print("SUMMARY:", summary)

        return jsonify({'summary': summary})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({'summary': "Oops! Something went wrong."})

if __name__ == '__main__':
    app.run(debug=True)
