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
- **Long-term memory:** Uses Mem0 and ChromaDB to extract, store and retrieve relevant user facts.

Memory correction and deletion capabilities are not yet implemented. Long-term memory retrieval through the Flask application is still being tested.

## 📌 Project Status

The retro terminal interface, Flask backend and local Ollama chat integration are working.

Mem0 and ChromaDB have been integrated, with further validation of live memory persistence still needed.

This is an ongoing open-source project.

## 🤝 Contributing

Contributions, suggestions and improvements are welcome!

Feel free to explore the repository, report issues and contribute.
