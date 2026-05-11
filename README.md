# 🤖 AutoShorts — AI Content Automation Engine

> Fully autonomous pipeline that generates, validates, and publishes YouTube Shorts with zero human intervention.

## What it Does

AutoShorts is an end-to-end AI content production system that runs 24/7:

1. **Script Generation** — LLM (Groq/Ollama) generates viral-optimized scripts
2. **Quality Validation** — 5-dimension AI judge scores each script (auto-reject + retry)
3. **Voice Synthesis** — Edge-TTS generates professional narration
4. **Video Assembly** — FFmpeg composites video with stock footage from Pexels
5. **Auto-Upload** — YouTube Data API v3 publishes with optimized metadata
6. **Scheduling** — Cron jobs run daily at optimal times with jittered uploads

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| AI/LLM | Groq API, Ollama (Llama 3) |
| Voice | Edge-TTS |
| Video | FFmpeg, MoviePy |
| Upload | YouTube Data API v3 |
| Database | SQLite (deduplication) |
| Stock Media | Pexels API |
| Scheduling | Cron + Custom Scheduler |

## Key Features

- **Zero Intervention** — Produces 4 videos/day autonomously
- **SAECS Prompt Framework** — Structured prompting for consistent quality
- **Deduplication Engine** — 60-day topic cooldown, 30-day clip cooldown
- **Quality Gate** — AI-powered 5-dimension scoring with auto-retry
- **Smart Scheduling** — Jittered upload times to mimic human behavior

## Architecture

```
User Config → Niche Selection → LLM Script Gen → Quality Validation
    → TTS Voice → Stock Footage → FFmpeg Assembly → YouTube Upload
    → Analytics Tracking → Next Cycle
```

## Setup

```bash
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
# Add your API keys
python scripts/pro_pipeline.py
```

## Author

**Azad Ansari** — [Portfolio](https://ansariazad.github.io) · [LinkedIn](https://linkedin.com/in/azad-ansari-902035297)
