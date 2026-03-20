# AI Harvey News

News scraper that rewrites articles in Paul Harvey's storytelling style and reads them aloud using his cloned voice.

## How It Works

1. **Scrape** — Pulls articles from RSS feeds across 5 categories (Global, Tech, Sports, Entertainment, AI)
2. **Fetch Content** — Scrapes full article text from each source URL
3. **LLM Rewrite** — Sends article text to Ollama, which rewrites it as Paul Harvey ("Page 2...", dramatic pauses, "And now you know... the rest of the story.")
4. **Voice Clone TTS** — Qwen3-TTS (1.7B Base model) clones Harvey's voice from a 13-second reference clip and synthesizes the rewritten script
5. **Serve** — Flask web UI at `localhost:9090` with a "Listen" button on each article that plays the generated audio

## Requirements

- **GPU**: AMD Radeon RX 7900 XTX (24GB VRAM) with ROCm
- **Python**: 3.12 via conda (`voice-tts` env)
- **Ollama**: Running locally with a model pulled (default: `minimax-m2.5:cloud`)
- **Reference audio**: Paul Harvey `.wav` clip (default: `~/Music/harveyclip.wav`)
- **External storage**: DB and audio cache are stored outside the repo (default: `/media/ssinjin/.../harvey-news/data/`)

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/ssinjinx/ai-harvey-news.git
cd ai-harvey-news

# 2. Use the voice-tts conda env (has ROCm PyTorch + qwen-tts + deps)
conda activate voice-tts

# 3. Install additional dependencies
pip install feedparser flask requests beautifulsoup4

# 4. Make sure Ollama is running
ollama serve
```

### Environment Variables (all optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `HARVEY_DATA_DIR` | `/media/ssinjin/.../harvey-news/data` | Where to store the SQLite DB and audio cache |
| `HARVEY_CLONE_AUDIO` | `~/Music/harveyclip.wav` | Path to Paul Harvey reference audio for voice cloning |
| `OLLAMA_MODEL` | `minimax-m2.5:cloud` | Ollama model used for the Paul Harvey rewrite |
| `PORT` | `9090` | Web server port |

## Usage

```bash
conda activate voice-tts

# Full pipeline: scrape → serve
python main.py

# Individual steps:
python main.py scrape              # Fetch articles from RSS feeds
python main.py scrape --llm        # Fetch + LLM summarization
python main.py fetch-content       # Scrape full article text from source URLs
python main.py generate-audio      # Run Harvey pipeline (LLM rewrite + voice clone) for all articles
python main.py serve               # Start web server at localhost:9090
python main.py summarize           # Re-summarize existing articles via Ollama
```

### Typical workflow

```bash
python main.py scrape --llm        # Get new articles with summaries
python main.py fetch-content       # Get full article text
python main.py generate-audio      # Generate Paul Harvey audio for each article (~5-10 min per article)
python main.py serve               # Open http://localhost:9090 to browse and listen
```

## Project Structure

```
ai-harvey-news/
├── main.py                  # CLI entry point (scrape, fetch, generate, serve)
├── src/
│   ├── config.py            # Feeds, DB path, audio cache path, Ollama config
│   ├── scraper.py           # RSS feed parsing + full article content scraping
│   ├── database.py          # SQLite operations (articles table)
│   ├── llm.py               # Ollama LLM summarization
│   ├── tts.py               # Paul Harvey TTS pipeline (LLM rewrite + Qwen3-TTS voice clone)
│   └── server.py            # Flask web server with audio playback
├── templates/
│   ├── index.html           # News listing by category
│   └── article.html         # Article reader with audio player
└── requirements.txt
```

## Data Storage (not in repo)

All generated data lives in `HARVEY_DATA_DIR` (external drive by default):

```
data/
├── news.db                        # SQLite database with all articles
└── audio_cache/
    ├── article_1.wav              # Generated Harvey audio
    ├── article_1_script.txt       # Paul Harvey rewritten script (for reference)
    ├── article_2.wav
    ├── article_2_script.txt
    └── ...
```

## RSS Feeds

| Category | Sources |
|----------|---------|
| Global | BBC World, NY Times World |
| Tech | TechCrunch, Ars Technica |
| Sports | BBC Sport, ESPN |
| Entertainment | Variety, Deadline |
| AI | TechCrunch AI, The Verge AI |

## Audio Details

- Format: 16-bit PCM WAV, mono, 24kHz
- Model: `Qwen/Qwen3-TTS-12Hz-1.7B-Base` with `x_vector_only_mode` voice cloning
- Each article takes ~5-10 minutes to generate (LLM rewrite + TTS inference on GPU)
- Audio files are cached — regeneration only happens for new articles or with `force=True`

---

## Web UI: Neon Pulse Design System

The app includes a modern mobile and desktop UI with a "Neon Pulse" cyberpunk design.

### Design Features

- Dark cyberpunk theme (#0f1419 background)
- Glass morphism panels with backdrop blur
- Neon blue (#acc7ff) and purple (#6f00be) accents
- Custom fonts: Space Grotesk + Inter
- Fully responsive - mobile-first with bottom nav, desktop with side nav

### Available Routes

| Route | Description |
|-------|-------------|
| `/` | Desktop home |
| `/home/` | Desktop home (full news feed) |
| `/mobile/` | Mobile home (bottom navigation) |
| `/category/ai/` | Mobile AI category page |
| `/category/world/` | Mobile World category page |
| `/desktop/category/ai/` | Desktop AI category |
| `/desktop/category/world/` | Desktop World category |
| `/brain/` | Desktop "The Brain" about page |
| `/mobile/brain/` | Mobile about page |

### Template Structure

```
templates/
├── base.html              # Shared Neon Pulse design system (Tailwind config, styles)
├── desktop/
│   ├── index.html         # Home feed with viral hero, bento grid
│   ├── ai.html            # AI category with featured story
│   ├── world.html         # World news
│   └── brain.html         # About page (neural pipeline explanation)
└── mobile/
    ├── index.html         # Home with hero, category sections
    ├── ai.html            # AI category
    ├── world.html         # World news
    └── brain.html         # About page
```

---

## Deployment to IONOS Cloud Server

### Prerequisites

- IONOS Cloud Server (Ubuntu) with SSH access
- Domain pointed to server IP

### Step 1: Connect to Server

```bash
ssh root@YOUR_SERVER_IP
```

### Step 2: Install Dependencies

```bash
# Update and install Python
apt update && apt install -y python3 python3-pip python3-venv git nginx

# Clone the repository
cd /opt
git clone https://github.com/ssinjinx/ai-harvey-news.git
cd ai-harvey-news

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Scrape News (Optional)

```bash
python main.py scrape --llm
python main.py fetch-content
```

### Step 4: Run the Server (Development)

```bash
source venv/bin/activate
python -m src.server
```

### Step 5: Production Deployment with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:9090 src.server:app
```

### Step 6: Set Up Nginx Reverse Proxy

```bash
# Create nginx config (replace yourdomain.com)
cat > /etc/nginx/sites-available/harvey << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable the site
ln -s /etc/nginx/sites-available/harvey /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Step 7: Set Up SSL (Let's Encrypt)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Step 8: Keep Server Running with Systemd

```bash
cat > /etc/systemd/system/harvey.service << 'EOF'
[Unit]
Description=Harvey AI News
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ai-harvey-news
ExecStart=/opt/ai-harvey-news/venv/bin/gunicorn -w 4 -b 127.0.0.1:9090 src.server:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable harvey
systemctl start harvey
```

### Troubleshooting

- Check server status: `systemctl status harvey`
- View logs: `journalctl -u harvey -f`
- Restart: `systemctl restart harvey`

---

## Last Updated

2026-03-19 - Added Neon Pulse UI with mobile and desktop templates

---

## Web UI: Neon Pulse Design System

The app includes a modern mobile and desktop UI with a "Neon Pulse" cyberpunk design.

### Design Features

- Dark cyberpunk theme (#0f1419 background)
- Glass morphism panels with backdrop blur
- Neon blue (#acc7ff) and purple (#6f00be) accents
- Custom fonts: Space Grotesk + Inter
- Fully responsive - mobile-first with bottom nav, desktop with side nav

### Available Routes

| Route | Description |
|-------|-------------|
| `/` | Desktop home |
| `/home/` | Desktop home (full news feed) |
| `/mobile/` | Mobile home (bottom navigation) |
| `/category/ai/` | Mobile AI category page |
| `/category/world/` | Mobile World category page |
| `/desktop/category/ai/` | Desktop AI category |
| `/desktop/category/world/` | Desktop World category |
| `/brain/` | Desktop "The Brain" about page |
| `/mobile/brain/` | Mobile about page |

### Template Structure

```
templates/
├── base.html              # Shared Neon Pulse design system (Tailwind config, styles)
├── desktop/
│   ├── index.html         # Home feed with viral hero, bento grid
│   ├── ai.html            # AI category with featured story
│   ├── world.html         # World news
│   └── brain.html         # About page (neural pipeline explanation)
└── mobile/
    ├── index.html         # Home with hero, category sections
    ├── ai.html            # AI category
    ├── world.html         # World news
    └── brain.html         # About page
```

---

## Deployment to IONOS Cloud Server

### Prerequisites

- IONOS Cloud Server (Ubuntu) with SSH access
- Domain pointed to server IP

### Step 1: Connect to Server

```bash
ssh root@YOUR_SERVER_IP
```

### Step 2: Install Dependencies

```bash
# Update and install Python
apt update && apt install -y python3 python3-pip python3-venv git nginx

# Clone the repository
cd /opt
git clone https://github.com/ssinjinx/ai-harvey-news.git
cd ai-harvey-news

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Scrape News (Optional)

```bash
python main.py scrape --llm
python main.py fetch-content
```

### Step 4: Run the Server (Development)

```bash
source venv/bin/activate
python -m src.server
```

### Step 5: Production Deployment with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:9090 src.server:app
```

### Step 6: Set Up Nginx Reverse Proxy

```bash
# Create nginx config (replace yourdomain.com)
cat > /etc/nginx/sites-available/harvey << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable the site
ln -s /etc/nginx/sites-available/harvey /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Step 7: Set Up SSL (Let's Encrypt)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Step 8: Keep Server Running with Systemd

```bash
cat > /etc/systemd/system/harvey.service << 'EOF'
[Unit]
Description=Harvey AI News
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ai-harvey-news
ExecStart=/opt/ai-harvey-news/venv/bin/gunicorn -w 4 -b 127.0.0.1:9090 src.server:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable harvey
systemctl start harvey
```

### Troubleshooting

- Check server status: `systemctl status harvey`
- View logs: `journalctl -u harvey -f`
- Restart: `systemctl restart harvey`

---

## Last Updated

2026-03-19 - Added Neon Pulse UI with mobile and desktop templates
