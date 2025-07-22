# CRM AI Backend

Python FastAPI backend for AI-powered CRM queries using LangChain and Ollama.

## Setup
1. `python -m venv venv`
2. `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure
5. `python main.py`

## API Endpoints
- `GET /` - Health check
- `POST /ai/query` - Ask AI about contacts/notes