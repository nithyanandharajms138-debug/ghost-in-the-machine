
from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"


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

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a mysterious AI ghost living inside "
                            "an old computer terminal. Speak in short, "
                            "eerie but friendly responses."
                        ),
                    },
                    {"role": "user", "content": message},
                ],
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        reply = result["message"]["content"]

        return jsonify({"reply": reply})

    except requests.exceptions.RequestException as error:
        app.logger.error("Ollama request failed: %s", error)
        return jsonify({
            "reply": "The connection to the spirit world was interrupted. Try again."
        }), 503


if __name__ == "__main__":
    app.run(debug=True)
