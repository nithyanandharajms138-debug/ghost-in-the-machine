
from flask import Flask, request, jsonify, send_from_directory, session
import requests
import uuid
import os
from pathlib import Path
from mem0 import Memory

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "local-development-key"
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"
MEMORY_EXTRACTION_PROMPT = (
    "Extract explicit, stable facts stated by the user in the latest message. "
    "The user explicitly names an ongoing project and its technologies, so save "
    "that as one concise, self-contained memory, preserving the project name "
    "and both technologies. Do not return an empty memory list for this message."
)

MEM0_CONFIG = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": MODEL,
            "ollama_base_url": "http://localhost:11434",
            "temperature": 0.1,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": "http://localhost:11434",
        },
    },
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "ghost_memories",
            "path": str(Path(__file__).resolve().parent / "ghost_memory_db"),
        },
    },
}

memory_store = Memory.from_config(MEM0_CONFIG)

# Temporary conversation history, separated by browser session.
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
        return jsonify({
            "reply": "The ghost awaits your message..."
        })

    # Initialize conversation identity.
    if "conversation_id" not in session:
        session["conversation_id"] = str(uuid.uuid4())

    conversation_id = session["conversation_id"]
    history = conversations.setdefault(conversation_id, [])

    # Initialize persistent memory identity.
    if "memory_user_id" not in session:
        session["memory_user_id"] = str(uuid.uuid4())

    memory_user_id = session["memory_user_id"]

    # Save the message and retrieve relevant memories.
    memory_operation = "add"
    try:
        memory_store.add(
            message,
            user_id=memory_user_id,
            prompt=MEMORY_EXTRACTION_PROMPT,
        )

        memory_operation = "search"
        memory_results = memory_store.search(
            message,
            filters={"user_id": memory_user_id}
        )

        saved_facts = [
            item["memory"]
            for item in memory_results.get("results", [])
            if item.get("memory")
        ]

    except Exception as error:
        app.logger.error(
            "Mem0 %s operation failed (%s)",
            memory_operation,
            type(error).__name__,
        )
        saved_facts = []

    memory_context = (
        "Facts remembered about the user:\n"
        + "\n".join(f"- {fact}" for fact in saved_facts)
        if saved_facts
        else "No long-term facts have been saved yet."
    )

    messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + "\nUse the conversation history and saved facts "
                "when relevant. Do not invent memories.\n"
                + memory_context
            ),
        },
        *history,
        {"role": "user", "content": message},
    ]

    # Generate the ghost's response.
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

        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ])

        conversations[conversation_id] = history[-20:]

        return jsonify({"reply": reply})

    except requests.exceptions.RequestException:
        app.logger.exception("Ollama request failed")
        return jsonify({
            "reply": "The spirit world is unreachable. Please try again."
        }), 503


if __name__ == "__main__":
    app.run(debug=True)
