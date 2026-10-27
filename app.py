
from flask import Flask, request, jsonify, send_from_directory, session
import requests
import uuid
import os

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "local-development-key"
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

# Temporary conversation storage, kept separately for each session.
conversations = {}

SYSTEM_PROMPT = (
    "You are a mysterious AI ghost living inside an old computer "
    "terminal. Speak in short, eerie but friendly responses."
)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def serve_files(filename):
    return send_from_directory(".", filename)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "The ghost awaits your message..."})

    # Give each browser session its own conversation ID.
    if "conversation_id" not in session:
        session["conversation_id"] = str(uuid.uuid4())

    conversation_id = session["conversation_id"]

    if conversation_id not in conversations:
        conversations[conversation_id] = []

    history = conversations[conversation_id]

    # Include earlier messages so the model has context.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": message},
    ]

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()

        reply = response.json()["message"]["content"]

        # Save both sides of the conversation.
        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ])

        # Keep only the latest 10 exchanges (20 messages).
        conversations[conversation_id] = history[-20:]

        return jsonify({"reply": reply})

    except requests.exceptions.RequestException:
        app.logger.exception("Ollama request failed")
        return jsonify({
            "reply": "The spirit world is unreachable. Please try again."
        }), 503


if __name__ == "__main__":
    app.run(debug=True)
