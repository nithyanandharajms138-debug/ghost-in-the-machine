# 👻 Ghost in the Machine

A spooky, retro terminal-style AI companion that lives inside your computer. Powered by locally running AI models, Ghost communicates through a mysterious terminal interface.

## ✨ Features

- Retro terminal-style interface built with HTML, CSS and JavaScript.
- Interactive AI conversation with a ghost character.
- Local AI responses using Ollama and Qwen2.5 3B.
- Python Flask backend.
- Mem0 integration for extracting and retrieving user memories.
- ChromaDB as the persistent vector store.
- Local-first architecture — no paid AI API key required.

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| AI Runtime | Ollama |
| Language Model | Qwen2.5 3B |
| Memory Framework | Mem0 |
| Vector Database | ChromaDB |
| Embedding Model | nomic-embed-text |

## 📋 Prerequisites

- Python
- Git
- Ollama
- Sufficient local resources to run the selected AI models

## 🚀 Run Locally

### 1. Install Ollama

Download Ollama from [ollama.com](https://ollama.com/download).

### 2. Download the required models

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text:latest
```

### 3. Clone the repository

```bash
git clone https://github.com/nithyanandharajms138-debug/ghost-in-the-machine.git
cd ghost-in-the-machine
```

### 4. Create a virtual environment

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Start the application

```bash
python app.py
```

### 7. Open Ghost

Visit:

http://127.0.0.1:5000

Make sure Ollama is running locally before starting the application.

## 🧠 Memory Architecture

Ghost uses two types of memory:

- **Short-term memory:** Maintains recent conversation history during the running Flask process.
- **Long-term memory:** Retrieves relevant facts from Mem0 and ChromaDB during the request. Automatic extraction runs in a background worker after the message is durably queued in `memory_jobs.sqlite3`; failed jobs are retried, and the existing ChromaDB collection remains the persistent memory store. To avoid competing with CPU-bound chat generation, the worker waits until chat has been idle for five seconds before processing queued messages.

Memory correction and deletion capabilities are not yet implemented. Newly extracted facts become available to retrieval after their background job succeeds. Pending chat text is stored locally in the SQLite queue until processed.

The background worker starts on the first request and is guarded against Flask's debug reloader starting a duplicate worker. If the queue cannot persist a message, the chat request returns a service-unavailable response rather than silently dropping the memory job. The queue database is local plaintext and is ignored by Git.

## 🧪 Test

Run these commands from the project directory with the project's virtual environment activated:

```powershell
python -m py_compile app.py test_memory_queue.py
python -m unittest test_memory_queue
python test_memory_persistence.py --verify
```

The persistence check uses the existing `ghost_memory_persistence_test_db`. To exercise live extraction and search instead, run `python test_mem0.py`; it writes to the separate `mem0_test_db` and requires both Ollama models to be available.

## 📌 Project Status

The retro terminal interface, Flask backend and local Ollama chat integration are working. Automatic Mem0 extraction, ChromaDB persistence, and fresh-process retrieval have been validated locally. Model cold-start time and CPU throughput remain machine-dependent.

This is an ongoing open-source project.

## 🤝 Contributing

Contributions, suggestions and improvements are welcome!

Feel free to explore the repository, report issues and contribute.
