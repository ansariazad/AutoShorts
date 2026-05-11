# 🎬 AutoShorts — Complete Setup Guide

> Fully automated YouTube Shorts factory using only FREE tools. Generates and uploads 1 trending Short per day with zero manual work.

---

## 📋 Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Python 3.10+** | Scripts runtime | `brew install python@3.12` |
| **FFmpeg** | Video processing | `brew install ffmpeg` |
| **Node.js 18+** | n8n runtime | `brew install node` |
| **n8n** | Workflow automation | `npm install -g n8n` |
| **Ollama** *(optional)* | Local AI model | [ollama.ai](https://ollama.ai) |

---

## 🚀 Step-by-Step Setup

### Step 1: Install System Dependencies

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install FFmpeg, Python, Node.js
brew install ffmpeg python@3.12 node

# Install n8n globally
npm install -g n8n
```

### Step 2: Install Python Packages

```bash
cd /Users/azad/Desktop/AutoShorts
pip3 install -r requirements.txt
```

### Step 3: Get Free API Keys

> All APIs below are **100% free**. See [FREE_APIS.md](FREE_APIS.md) for full details.

#### 🎥 Pexels API (Stock Video)
1. Go to [pexels.com/api](https://www.pexels.com/api/)
2. Click **"Get Started"** → Create free account
3. Copy your API key
4. Paste into `config/config.yaml` → `pexels_api_key`

#### 🎥 Pixabay API (Backup Stock Video)
1. Go to [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Sign up for free → Get API key
3. Paste into `config/config.yaml` → `pixabay_api_key`

#### 🤖 Groq API (Free AI — Fallback)
1. Go to [console.groq.com](https://console.groq.com)
2. Create free account → Get API key
3. Paste into `config/config.yaml` → `groq_api_key`

### Step 4: Set Up Ollama (Free Local AI)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download the model (one-time, ~2GB)
ollama pull llama3.2

# Start Ollama server (runs in background)
ollama serve
```

### Step 5: Set Up YouTube Upload

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (e.g., "AutoShorts")
3. Enable **YouTube Data API v3**:
   - Go to **APIs & Services → Library**
   - Search "YouTube Data API v3" → **Enable**
4. Create OAuth2 Credentials:
   - Go to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download the JSON file
   - Save as `config/client_secrets.json`
5. Add your Google account to **OAuth consent screen → Test users**
6. First-time auth (run once):
```bash
python3 scripts/upload_to_youtube.py
# A browser window will open — sign in with your YouTube account
# The token is saved and auto-refreshes after that
```

### Step 6: Set Up Google Sheets Logging

1. In the same Google Cloud project, enable **Google Sheets API** and **Google Drive API**
2. Create a **Service Account**:
   - Go to **IAM & Admin → Service Accounts**
   - Create account → Download JSON key
   - Save as `config/service_account.json`
3. Create a new Google Sheet for logging
4. **Share the sheet** with the service account email (from the JSON file)
5. Copy the Spreadsheet ID from the URL:
   - URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
   - Paste into `config/config.yaml` → `spreadsheet_id`

### Step 7: Import n8n Workflow

```bash
# Start n8n
n8n start

# Open n8n in browser: http://localhost:5678
```

1. Go to **Workflows → Import from File**
2. Select `n8n_workflow.json`
3. The workflow will load with all 7 pipeline nodes
4. Click **"Activate"** to enable the daily schedule
5. Click **"Execute Workflow"** to test it manually

### Step 8: Test the Pipeline

```bash
# Full test (generates video but skips upload)
bash run_pipeline.sh --dry-run

# Test with upload
bash run_pipeline.sh

# Test individual steps
python3 scripts/generate_script.py --test
python3 scripts/generate_voice.py
python3 scripts/download_stock_video.py
python3 scripts/assemble_video.py
```

---

## 📁 Project Structure

```
AutoShorts/
├── scripts/
│   ├── generate_script.py      ← AI script + trending topics
│   ├── generate_voice.py       ← Text-to-speech (edge-tts)
│   ├── download_stock_video.py ← Stock footage (Pexels/Pixabay)
│   ├── assemble_video.py       ← FFmpeg video builder
│   ├── upload_to_youtube.py    ← YouTube uploader
│   └── log_to_sheets.py        ← Google Sheets tracker
├── config/
│   ├── config.yaml             ← All settings & API keys
│   ├── client_secrets.json     ← YouTube OAuth (you create)
│   ├── youtube_token.json      ← Auto-generated after first auth
│   └── service_account.json    ← Google Sheets key (you create)
├── assets/music/               ← Drop royalty-free MP3s here
├── temp/                       ← Working files (auto-cleaned)
├── output/                     ← Final MP4 videos + logs
├── n8n_workflow.json           ← Import into n8n
├── run_pipeline.sh             ← Master orchestration script
└── requirements.txt            ← Python dependencies
```

---

## 🎵 Adding Background Music (Optional)

Drop any **royalty-free** MP3 files into `assets/music/`. The system will randomly pick one for each video.

Free music sources:
- [Pixabay Music](https://pixabay.com/music/) — 100% free, no attribution
- [Mixkit](https://mixkit.co/free-stock-music/) — Free music tracks
- [YouTube Audio Library](https://studio.youtube.com/channel/UC/music) — Free for YouTube

---

## 🔄 Auto-Start on Boot (Optional)

Create a macOS LaunchAgent to start n8n automatically:

```bash
cat > ~/Library/LaunchAgents/com.autoshorts.n8n.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.autoshorts.n8n</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/n8n</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/azad/Desktop/AutoShorts/output/n8n.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/azad/Desktop/AutoShorts/output/n8n_error.log</string>
</dict>
</plist>
EOF

# Load it
launchctl load ~/Library/LaunchAgents/com.autoshorts.n8n.plist
```

---

## 💰 YouTube Monetization Strategy (Under 30 Days)

### Requirements for YouTube Partner Program
- **500 subscribers** + **3,000 watch hours** OR **3 million Shorts views in 90 days**

### Growth Tactics for Fast Monetization

1. **Post 2-3 Shorts per day** (change `triggerAtHour` in the n8n workflow to add multiple triggers)
2. **Focus on curiosity-gap titles** — "You won't believe..." / "This is why..."
3. **First 3 seconds = HOOK** — the script generator is already optimized for this
4. **Use trending topics** — the system auto-fetches from Google Trends & Reddit
5. **Niche down** — pick 2-3 related niches (e.g., psychology + self-improvement + facts)
6. **Consistent posting time** — the cron trigger handles this automatically
7. **Engage with comments** — the one manual thing that really helps growth

### Recommended Niches for Fast Growth
- 🧠 Psychology & mind-blowing facts
- 💪 Self-improvement & motivation
- 🌍 Geography & travel facts
- 🔬 Science & space
- 📱 Tech tips & AI news
- 🏛️ History & mysteries

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ffmpeg: command not found` | Run `brew install ffmpeg` |
| `edge-tts` not working | Run `pip3 install edge-tts --upgrade` |
| Ollama not responding | Start it with `ollama serve` |
| YouTube upload quota exceeded | Wait 24h (resets daily at midnight PT) |
| No stock videos found | Check Pexels/Pixabay API keys in config.yaml |
| n8n not starting | Try `npx n8n start` instead |
