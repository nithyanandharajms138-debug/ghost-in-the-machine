# Ghost in the Machine 👻

A spooky, retro terminal-style web application powered by a locally running AI model.

## Features

- Retro terminal interface built with HTML and CSS
- Interactive chat using JavaScript
- Python Flask backend
- Local AI responses powered by Ollama and Qwen2.5 3B
- No paid AI API key required

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Local AI runtime:** Ollama
- **AI model:** Qwen2.5 3B

## Prerequisites

- Python
- Ollama for Windows or another supported operating system
- Git (optional, for cloning the repository)

## Run Locally

1. Install [Ollama](https://ollama.com/download).
2. Download the model:

   ```bash
   ollama pull qwen2.5:3b
   ```

3. Clone this repository and enter the project folder:

   ```bash
   git clone YOUR_REPOSITORY_URL
   cd ghost-in-the-machine
   ```

4. Create and activate a Python virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

6. Start the Flask server:

   ```powershell
   py app.py
   ```

7. Open http://127.0.0.1:5000 in your browser.

**Note:** Ollama must be running locally with the `qwen2.5:3b` model available.

## Project Status

The basic terminal interface, Flask backend, and local AI integration are working. Further improvements are planned.
