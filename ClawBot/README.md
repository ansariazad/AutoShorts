# 🧠 ClawBot — Autonomous AI Mac Agent

> AI-powered assistant with 32+ tools that controls your Mac via Telegram. System control, trading, messaging, and file management — all through natural language.

## What it Does

ClawBot is an autonomous AI agent that takes a single Telegram message and executes complex multi-step tasks on your Mac:

- **System Control** — Open apps, manage windows, adjust volume, take screenshots
- **Messaging** — Send WhatsApp messages, emails via AppleScript
- **Trading** — Real-time crypto/stock monitoring via CoinGecko & Yahoo Finance
- **File Management** — Search, read, create, and organize files
- **Web Automation** — Open URLs, search Google, scrape content
- **Security** — Dangerous command detection + owner-only confirmation

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| AI/LLM | Groq API (Llama 3, Mixtral) |
| Interface | Telegram Bot API |
| System | AppleScript, subprocess |
| Markets | CoinGecko API, Yahoo Finance |
| Config | YAML |

## Architecture

```
Telegram Message → LLM Reasoning → Tool Selection → JSON Args
    → Tool Execution → Result → LLM Summary → Telegram Reply
    → Multi-tool Chaining (if needed)
```

## Key Features

- **32+ Tools** spanning 8 categories
- **LLM Tool-Calling** with JSON reasoning chain
- **Multi-Tool Chaining** — execute complex workflows
- **Memory System** — retains conversation context
- **Security Layer** — blocks destructive commands without confirmation

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
# Add Groq API key + Telegram bot token
python main.py
```

## Author

**Azad Ansari** — [Portfolio](https://ansariazad.github.io) · [LinkedIn](https://linkedin.com/in/azad-ansari-902035297)
