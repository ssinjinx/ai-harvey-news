# AI Harvey News Reader

AI-powered news scraper with local LLM summarization and text-to-speech.

## Features

- **News Scraping** — Pull headlines from multiple sources
- **Local LLM** — Summarize articles using your 7900 XTX (kimi-k2.5 via Ollama)
- **Text-to-Speech** — Convert summaries to audio
- **Scheduled Updates** — Cron-based news fetching

## Tech Stack

- Python (scraping + LLM integration)
- Ollama (local LLM)
- SQLite (article storage)
- TTS library (elevenlabs, pyttsx3, or similar)

## Project Structure

```
ai-harvey-news/
├── src/
│   ├── scraper/          # News scraping modules
│   ├── llm/              # LLM summarization
│   ├── tts/              # Text-to-speech
│   └── scheduler/        # Cron job management
├── data/
│   └── articles.db       # SQLite database
├── audio/                # Generated audio files
├── config.yaml           # Configuration
└── README.md
```

## Status

🚧 Work in progress

## Created

2026-03-16
