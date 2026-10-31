
import os
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory, session
from mem0 import Memory


app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "local-development-key"
)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL = "qwen2.5:3b"
MEMORY_QUEUE_PATH = Path(__file__).resolve().parent / "memory_jobs.sqlite3"
MEMORY_JOB_LEASE_SECONDS = 300
MEMORY_IDLE_DELAY_SECONDS = 5
MEMORY_EXTRACTION_TIMEOUT_SECONDS = 180
MEMORY_EMBEDDING_TIMEOUT_SECONDS = 30
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
            "ollama_base_url": OLLAMA_BASE_URL,
            "temperature": 0.1,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": OLLAMA_BASE_URL,
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

# Mem0's Ollama clients otherwise have no request timeout.
for component, timeout in (
    (memory_store.llm, MEMORY_EXTRACTION_TIMEOUT_SECONDS),
    (memory_store.embedding_model, MEMORY_EMBEDDING_TIMEOUT_SECONDS),
):
    old_client = component.client
    component.client = type(old_client)(host=OLLAMA_BASE_URL, timeout=timeout)
    old_client.close()

# Temporary conversation history, separated by browser session.
conversations = {}
_memory_worker = None
_memory_worker_lock = threading.Lock()
_chat_activity_lock = threading.Lock()
_active_chat_requests = 0
_last_chat_activity = 0.0

SYSTEM_PROMPT = (
    "You are a mysterious AI ghost living inside an old computer "
    "terminal. Speak in short, eerie but friendly responses."
)


def _connect_memory_queue():
    return sqlite3.connect(MEMORY_QUEUE_PATH, timeout=5)


def _process_is_running(process_id):
    try:
        os.kill(process_id, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _initialize_memory_queue():
    now = time.time()
    with closing(_connect_memory_queue()) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at REAL NOT NULL DEFAULT 0,
                claimed_pid INTEGER,
                lease_until REAL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_jobs_ready "
            "ON memory_jobs(status, available_at, id)"
        )

        claimed_jobs = connection.execute(
            "SELECT id, claimed_pid, lease_until FROM memory_jobs "
            "WHERE status = 'processing'"
        ).fetchall()
        for job_id, process_id, lease_until in claimed_jobs:
            if (
                lease_until is None
                or lease_until <= now
                or process_id is None
                or not _process_is_running(process_id)
            ):
                connection.execute(
                    """
                    UPDATE memory_jobs
                    SET status = 'pending', claimed_pid = NULL, lease_until = NULL
                    WHERE id = ? AND status = 'processing'
                    """,
                    (job_id,),
                )
        connection.commit()


def _enqueue_memory_job(user_id, message):
    with closing(_connect_memory_queue()) as connection:
        cursor = connection.execute(
            "INSERT INTO memory_jobs (user_id, message) VALUES (?, ?)",
            (user_id, message),
        )
        connection.commit()
        return cursor.lastrowid


def _claim_memory_job():
    now = time.time()
    with closing(_connect_memory_queue()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            UPDATE memory_jobs
            SET status = 'pending', claimed_pid = NULL, lease_until = NULL
            WHERE status = 'processing' AND lease_until <= ?
            """,
            (now,),
        )
        job = connection.execute(
            """
            SELECT id, user_id, message, attempts
            FROM memory_jobs
            WHERE status = 'pending' AND available_at <= ?
            ORDER BY id
            LIMIT 1
            """,
            (now,),
        ).fetchone()
        if job is None:
            connection.commit()
            return None

        job_id, user_id, message, attempts = job
        connection.execute(
            """
            UPDATE memory_jobs
            SET status = 'processing', attempts = attempts + 1,
                claimed_pid = ?, lease_until = ?
            WHERE id = ? AND status = 'pending'
            """,
            (
                os.getpid(),
                now + MEMORY_JOB_LEASE_SECONDS,
                job_id,
            ),
        )
        connection.commit()
        return job_id, user_id, message, attempts + 1


def _complete_memory_job(job_id):
    with closing(_connect_memory_queue()) as connection:
        connection.execute(
            "DELETE FROM memory_jobs WHERE id = ?",
            (job_id,),
        )
        connection.commit()


def _retry_memory_job(job_id, attempts):
    delay = min(2 ** attempts, 60)
    with closing(_connect_memory_queue()) as connection:
        connection.execute(
            """
            UPDATE memory_jobs
            SET status = 'pending', available_at = ?,
                claimed_pid = NULL, lease_until = NULL
            WHERE id = ?
            """,
            (time.time() + delay, job_id),
        )
        connection.commit()
    return delay


def _chat_is_idle():
    with _chat_activity_lock:
        return (
            _active_chat_requests == 0
            and (
                _last_chat_activity == 0
                or time.monotonic() - _last_chat_activity >= MEMORY_IDLE_DELAY_SECONDS
            )
        )


def _memory_worker_loop():
    while True:
        if not _chat_is_idle():
            time.sleep(0.5)
            continue

        try:
            job = _claim_memory_job()
        except Exception as error:
            app.logger.error(
                "Could not read the memory queue (%s)",
                type(error).__name__,
            )
            time.sleep(5)
            continue

        if job is None:
            time.sleep(0.5)
            continue

        job_id, user_id, message, attempts = job
        try:
            memory_store.add(
                message,
                user_id=user_id,
                prompt=MEMORY_EXTRACTION_PROMPT,
                infer=True,
            )
        except Exception as error:
            try:
                delay = _retry_memory_job(job_id, attempts)
            except Exception as queue_error:
                app.logger.error(
                    "Could not reschedule memory job %s (%s); it remains "
                    "recoverable from the queue",
                    job_id,
                    type(queue_error).__name__,
                )
                time.sleep(1)
                continue
            app.logger.error(
                "Mem0 extraction for queued job %s failed (%s); retrying in %s seconds",
                job_id,
                type(error).__name__,
                delay,
            )
        else:
            try:
                _complete_memory_job(job_id)
            except Exception as error:
                app.logger.error(
                    "Could not acknowledge completed memory job %s (%s); "
                    "it may be retried",
                    job_id,
                    type(error).__name__,
                )


@app.before_request
def _track_chat_request_start():
    global _active_chat_requests

    if request.endpoint == "chat":
        with _chat_activity_lock:
            _active_chat_requests += 1


@app.after_request
def _track_chat_request_finish(response):
    global _active_chat_requests, _last_chat_activity

    if request.endpoint == "chat":
        with _chat_activity_lock:
            _active_chat_requests -= 1
            _last_chat_activity = time.monotonic()
    return response


def _start_memory_worker():
    global _memory_worker

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    with _memory_worker_lock:
        if _memory_worker is not None and _memory_worker.is_alive():
            return

        _initialize_memory_queue()
        _memory_worker = threading.Thread(
            target=_memory_worker_loop,
            name="memory-extraction-worker",
            daemon=True,
        )
        _memory_worker.start()


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

    try:
        _start_memory_worker()
        _enqueue_memory_job(memory_user_id, message)
    except Exception as error:
        app.logger.error(
            "Could not persist chat message for memory extraction (%s)",
            type(error).__name__,
        )
        return jsonify({
            "reply": "Memory storage is temporarily unavailable. Please try again."
        }), 503

    # Retrieve existing memories synchronously so they can be used in this reply.
    try:
        memory_results = memory_store.search(
            message,
            filters={"user_id": memory_user_id},
            top_k=5,
        )

        saved_facts = [
            item["memory"]
            for item in memory_results.get("results", [])
            if item.get("memory")
        ]
    except Exception as error:
        app.logger.error(
            "Mem0 search operation failed (%s)",
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
                "keep_alive": "10m",
                "options": {
                    "num_predict": 120,
                },
            },
            timeout=(3.05, 120),
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
