from flask import Flask, request, jsonify, render_template
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q')

    # TEMP: Simulated Reddit comments (replace later!)
    comments = [
        "The Sony WH-1000XM5 are amazing for noise cancelling and battery life.",
        "I really like the Bose QC45, super comfortable and solid sound quality."
    ]

    # Prompt to GPT
    prompt = f"Summarize these Reddit comments into the top product recommendations:\n{chr(10).join(comments)}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        print("SUMMARY:", summary)  # 🐛 Debug line to verify output

        return jsonify({'summary': summary})

    except Exception as e:
        print("ERROR:", e)  # 🐛 Debug error print
        return jsonify({'summary': "Oops! Something went wrong."})

if __name__ == '__main__':
    app.run(debug=True)
