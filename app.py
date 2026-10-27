
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Temporary response until we connect the AI model
    reply = f"I have received your message: {message}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
