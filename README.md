# Serverless ASCII-Box Chat on Vercel

This project implements a lightweight, command-line chat system that runs **entirely on the Vercel serverless platform**, using Vercel KV for state management.

This is a revised architecture that uses HTTP polling instead of UDP to be fully compatible with Vercel's serverless environment.

## Features

- **Fully Serverless Backend:** The entire backend is hosted on Vercel.
- **CLI Interface:** A clean, terminal-based chat experience.
- **Near Real-time Chat:** Clients poll for updates every few seconds.
- **User Presence:** See who is online (`--active`) with automatic cleanup of idle users.
- **AI Assistant:** Ask questions to a Google Gemini-powered AI (`--ai "your question"`).
- **Persistent History:** Chat history is maintained in Vercel KV.

## Architecture

- **Client (`client.py`):** A local Python application that users run in their terminal.
- **Backend (Vercel Serverless Functions):**
    - `api/chat.py`: An HTTP endpoint that handles all chat logic: login, sending messages, presence (heartbeats), and providing updates to clients.
    - `api/ai.py`: A separate HTTP endpoint for handling AI queries.
- **State Store (Vercel KV):** A serverless Redis database that stores the list of active users and the chat message history, allowing the stateless functions to manage persistent data.

## Setup and Installation

### 1. Prerequisites

- A Vercel account (Pro tier recommended for KV, but a free trial is available).
- Python 3.8+
- Git and `pip`
- Vercel CLI (`npm install -g vercel`)

### 2. API Keys

You need API keys for Google Search and Google Gemini.

1.  **Google Gemini API Key:** Get one from [Google AI Studio](https://makersuite.google.com/).
2.  **Google Cloud Platform API Key:**
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Create a project, enable the **"Custom Search API"**, and create an API Key.
3.  **Google Custom Search Engine ID (CSE ID):**
    - Go to the [Programmable Search Engine control panel](https://programmablesearchengine.google.com/).
    - Create a new search engine and copy the "Search engine ID".

### 3. Project Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd <your-repo-name>

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Log in to Vercel
vercel login

# Link the project to your Vercel account
vercel link
