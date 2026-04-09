# AI Harvey News

News scraper that rewrites articles in Paul Harvey's storytelling style and reads them aloud using his cloned voice.

## How It Works

1. **Scrape** — Pulls articles from RSS feeds across 5 categories (Global, Tech, Sports, Entertainment, AI)
2. **Fetch Content** — Scrapes full article text from each source URL
3. **LLM Rewrite** — Sends article text to Ollama, which rewrites it as Paul Harvey ("Page 2...", dramatic pauses, "And now you know... the rest of the story.")
4. **Voice Clone TTS** — ComfyUI runs Qwen3-TTS (1.7B) with a 5-second reference clip to clone Harvey's voice and synthesize the rewritten script
5. **Serve** — Flask web UI at `localhost:9090` with a "Listen" button on each article that plays the generated audio

## Requirements

- **ComfyUI**: Running locally at `http://localhost:8188` with the `FB_Qwen3TTSVoiceClone` custom node installed
- **GPU**: NVIDIA (tested on RTX 5060 Ti 16GB) or AMD RX 7900 XTX (24GB) with ROCm
- **Python**: 3.12 via venv
- **Ollama**: Running locally with a model pulled (default: `minimax-m2.5:cloud`)
- **Reference audio**: 5-second Paul Harvey `.wav` clip in ComfyUI's input directory (`harveyclip_5s.wav`)
- **ffmpeg**: For MP3 → WAV conversion after ComfyUI generates audio

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/ssinjinx/ai-harvey-news.git
cd ai-harvey-news

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install audio conversion (required for MP3 → WAV)
# Ubuntu/Debian: apt install ffmpeg

# 5. Make sure Ollama is running
ollama serve

# 6. Make sure ComfyUI is running with the Qwen3-TTS node
# See the ComfyUI Setup section below
```

### Environment Variables (all optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `HARVEY_DATA_DIR` | `/media/ssinjin/.../harvey-news/data` | Where to store the SQLite DB and audio cache |
| `HARVEY_CLONE_AUDIO` | `~/Music/harveyclip.wav` | Path to Paul Harvey reference audio (copied to ComfyUI automatically) |
| `COMFYUI_URL` | `http://localhost:8188` | ComfyUI server URL |
| `COMFYUI_DIR` | `/media/ssinjin/.../ComfyUI` | ComfyUI installation directory (for finding output files) |
| `OLLAMA_MODEL` | `minimax-m2.5:cloud` | Ollama model used for the Paul Harvey rewrite |
| `PORT` | `9090` | Web server port |

## Usage

```bash
source venv/bin/activate

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

### Standalone TTS script

```bash
# Use the default script file
python generate_harvey_tts.py

# Use a custom script file
python generate_harvey_tts.py my_script.txt

# Use inline text
python generate_harvey_tts.py --text "Good day, everyone. This is Harvey."

# Custom output path
python generate_harvey_tts.py --output /path/to/output.wav
```

### Typical workflow

```bash
python main.py scrape --llm        # Get new articles with summaries
python main.py fetch-content       # Get full article text
python main.py generate-audio      # Generate Paul Harvey audio via ComfyUI (~2-3 min per article)
python main.py serve               # Open http://localhost:9090 to browse and listen
```

## Project Structure

```
ai-harvey-news/
├── main.py                  # CLI entry point (scrape, fetch, generate, serve)
├── generate_harvey_tts.py  # Standalone TTS script (uses ComfyUI API)
├── src/
│   ├── config.py            # Feeds, DB path, audio cache path, Ollama/ComfyUI config
│   ├── scraper.py           # RSS feed parsing + full article content scraping
│   ├── database.py          # SQLite operations (articles table)
│   ├── llm.py               # Ollama LLM summarization
│   ├── tts.py               # Paul Harvey TTS pipeline (Ollama rewrite → ComfyUI voice clone)
│   └── server.py            # Flask web server with audio playback
├── comfyui/
│   ├── start_comfyui.sh     # Start ComfyUI with NVIDIA/AMD GPU env vars
│   ├── harveycyborg.png     # Harvey reference face image (for video)
│   └── harveyclip_5s.wav    # Harvey voice reference clip (5s)
├── templates/               # Jinja2 HTML templates (Neon Pulse design)
├── static/                  # Static assets (images, video)
└── requirements.txt
```

## Data Storage (not in repo)

All generated data lives in `HARVEY_DATA_DIR` (external drive by default):

```
data/
├── news.db                        # SQLite database with all articles
└── audio_cache/
    ├── ainewsarticle_21.wav       # Generated Harvey audio
    ├── ainewsarticle_21_script.txt  # Paul Harvey rewritten script (for reference)
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

- **Pipeline**: Ollama (LLM rewrite) → ComfyUI Qwen3-TTS (voice clone) → ffmpeg (MP3 → WAV)
- **Format**: 16-bit PCM WAV, mono, 24kHz
- **Model**: Qwen3-TTS 1.7B with voice cloning via 5-second reference clip
- **Reference audio**: `harveyclip_5s.wav` (5-second Paul Harvey clip in ComfyUI input directory)
- **Generation time**: ~2-3 minutes per article (ComfyUI inference on RTX 5060 Ti)
- **Audio files are cached** — regeneration only happens for new articles or with `force=True`

---

## ComfyUI Setup

The TTS pipeline uses ComfyUI as a backend. You need ComfyUI running with the Qwen3-TTS voice clone node.

### Required Custom Nodes

| Node | Repository | Purpose |
|------|-----------|---------|
| FB_Qwen3TTSVoiceClone | [ComfyUI-Qwen-TTS](https://github.com/flybirdxx/ComfyUI-Qwen-TTS) | Voice cloning TTS |
| easy positive | [comfyui-easy-use](https://github.com/yolain/ComfyUI-Easy-Use) | Text input helper |
| SaveAudioMP3 | Built-in (ComfyUI ≥0.18) | MP3 output |

### Required Models

Place in your ComfyUI `models/` directory:

| Model | Path | Notes |
|-------|------|-------|
| Qwen3-TTS-12Hz-1.7B-Base | `models/Qwen-TTS/` | Downloaded automatically by the node |

### Input Files

Ensure these files exist in ComfyUI's `input/` directory:

| File | Description |
|------|-------------|
| `harveyclip_5s.wav` | 5-second Paul Harvey voice reference clip |
| `harvey_ref_audio.wav` | Auto-copied from `HARVEY_CLONE_AUDIO` if missing |

### Starting ComfyUI

```bash
# NVIDIA GPU
bash ~/ai-harvey-news/comfyui/start_comfyui.sh

# Or if ComfyUI is at a custom path:
COMFYUI_DIR=/path/to/ComfyUI bash ~/ai-harvey-news/comfyui/start_comfyui.sh
```

ComfyUI will be available at `http://localhost:8188`.

The script auto-detects GPU type (NVIDIA/AMD) and sets the correct environment variables:

| GPU | Environment Variables |
|-----|----------------------|
| NVIDIA | `LD_LIBRARY_PATH` for CUDA |
| AMD | `HSA_OVERRIDE_GFX_VERSION=11.0.0`, `PYTORCH_ALLOC_CONF`, `FLASH_ATTENTION_TRITON_AMD_ENABLE` |

### Workflow

The TTS pipeline submits a workflow via the ComfyUI API with these nodes:

1. **easy positive** (×2) — Reference text + speech text inputs
2. **LoadAudio** — Loads `harveyclip_5s.wav` as the voice reference
3. **FB_Qwen3TTSVoiceClone** — Qwen3-TTS 1.7B model with voice cloning
4. **SaveAudioMP3** — Saves generated audio as MP3
5. **LayerUtility: PurgeVRAM V2** — Frees GPU memory after generation

The workflow JSON is defined inline in `src/tts.py` — no external workflow file needed.

---

## InfiniteTalk Video Generation (ComfyUI)

Harvey is animated as a talking-head video using WAN 2.1 InfiniteTalk. The video appears as a small portrait widget on the website — rendered locally via ComfyUI and synced to his cloned voice audio.

### Output

- **Resolution:** 240×416 (portrait)
- **Format:** H.264 MP4 with audio
- **Generation time:** ~2 min per 5 seconds of audio, ~1 hour for 3 minutes
- **VRAM peak:** ~18.6 GB (requires 24 GB GPU)

### Models Required

Place in your ComfyUI model directories:

| Model | Location | Size |
|-------|----------|------|
| `wan2.1-i2v-14b-480p-Q3_K_S.gguf` | `models/unet/` | ~6.8 GB |
| `Wan2_1-InfiniteTalk_Single_Q4_K_M.gguf` | `models/unet/` | ~4.6 GB |
| `umt5-xxl-enc-fp8_e4m3fn.safetensors` | `models/text_encoders/` | ~5.8 GB |
| `wan_2.1_vae.safetensors` | `models/vae/` | ~0.4 GB |
| `clip_vision_h.safetensors` | `models/clip_vision/` | ~0.6 GB |
| `lightx2v_I2V_14B_480p_cfg_step_distill_rank32_bf16.safetensors` | `models/loras/` | ~0.5 GB |

### Custom Nodes Required

- [ComfyUI-WanVideoWrapper](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [ComfyUI_KJNodes](https://github.com/kijai/ComfyUI-KJNodes)

### Starting ComfyUI

```bash
# Start ComfyUI with AMD ROCm env vars (from anywhere)
bash ~/ai-harvey-news/comfyui/start_comfyui.sh

# Or if ComfyUI is somewhere else:
COMFYUI_DIR=/path/to/ComfyUI bash ~/ai-harvey-news/comfyui/start_comfyui.sh
```

ComfyUI will be available at `http://localhost:8188`.

Key flags set by the script:
- `HSA_OVERRIDE_GFX_VERSION=11.0.0` — required for RX 7900 XTX on ROCm
- `PYTORCH_ALLOC_CONF=expandable_segments:True` — prevents VRAM fragmentation
- `python3 -u` — unbuffered output so logs appear in real time (needed for debugging hangs)
- `--use-sage-attention` — faster attention for AMD

### Adding Input Files

Place files in `~/ComfyUI/input/` before submitting:

```bash
# Face image (reference for the talking head)
cp myface.png ~/ComfyUI/input/

# Audio clip (the voice Harvey will lip-sync to)
cp myscript.wav ~/ComfyUI/input/
```

The workflow references files by filename only — no path needed in the JSON.

To trim audio to a specific length (requires ffmpeg):
```bash
ffmpeg -i full_audio.wav -t 5 -c copy harveyclip_5s.wav
```

### Submitting a Video Job

```bash
cd ~/ai-harvey-news/comfyui/

# Use defaults (harveycyborg.png + harveyclip_5s.wav, 240x416)
python submit.py

# Custom face + audio
python submit.py --image myface.png --audio myscript.wav

# Different resolution (portrait only — height must be > width)
python submit.py --width 480 --height 832 --prefix MyOutput
```

Output video lands in `~/ComfyUI/output/` with the prefix you specified.

### Critical Settings (AMD ROCm / 15 GB RAM)

These were required to prevent OOM crashes on a system with 15 GB RAM and 24 GB VRAM:

| Node | Setting | Value | Why |
|------|---------|-------|-----|
| `WanVideoTextEncode` | `device` | `cpu` | Keeps T5 (~5.8 GB) off VRAM entirely |
| `WanVideoTextEncode` | `force_offload` | `false` | Avoids 30+ min ROCm GPU→CPU transfer hang |
| `WanVideoLoraSelect` | `merge_loras` | `false` | GGUF models cannot merge LoRAs |
| `WanVideoBlockSwap` | `blocks_to_swap` | `0` | Block swap moves WAN blocks to CPU RAM as fp16 — OOM kills process on 15 GB RAM |
| `WanVideoImageToVideoMultiTalk` | `tiled_vae` | `true` | Reduces VAE peak VRAM |
| `WanVideoDecode` | `enable_vae_tiling` | `true` | Same |

### VRAM Profile

| Stage | VRAM Used |
|-------|-----------|
| Model loading | ~15.5 GB |
| Sampling (steady) | ~17 GB |
| Sampling (peak) | ~18.6 GB |

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

### Server Details

| | |
|---|---|
| **Live URL** | https://ai-harvey-news.silconsoul.cloud |
| **Server IP** | 162.222.206.135 |
| **SSH user** | `root` |
| **SSH password** | `gcD0RCEE4MNNqn` |
| **OS** | Ubuntu 24.04 |
| **Specs** | 4 vCore, 8 GB RAM, 240 GB NVMe |
| **App path** | `/opt/ai-harvey-news` |
| **Process** | gunicorn (no systemd — manual restart) |
| **Panel** | Plesk (https://162.222.206.135:8443) |
| **Hosted at** | IONOS Cloud, US datacenter |

> **IMPORTANT — Cloudflare proxy:** The domain points to Cloudflare IPs, not the server directly.
> Always SSH to the **IP** (`162.222.206.135`), never the domain.

> **IMPORTANT — IONOS Firewall:** The server has a firewall policy ("My firewall policy") that blocks
> all inbound traffic by default. If SSH times out, you must add an inbound rule for **TCP port 22**
> (or all ports) in the IONOS Cloud console:
> **Cloud Console → Server → Networking → Firewall → Edit policy → Add rule → TCP / Port 22 / Any source**

### Quick Deploy (one command)

```bash
sshpass -p "gcD0RCEE4MNNqn" ssh -o StrictHostKeyChecking=no root@162.222.206.135 \
  "cd /opt/ai-harvey-news && git pull origin master && pkill -f gunicorn; gunicorn -w 4 -b 127.0.0.1:9090 src.server:app --daemon"
```

Or just run the included script:

```bash
bash deploy.sh
```

### Step 1: Connect to Server

```bash
ssh root@162.222.206.135
# password: gcD0RCEE4MNNqn
```

### Step 2: Install Dependencies

```bash
apt update && apt install -y python3 python3-pip python3-venv git nginx
cd /opt
git clone https://github.com/ssinjinx/ai-harvey-news.git
cd ai-harvey-news
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run the Server

```bash
source venv/bin/activate
python -m src.server
```

### Step 4: Production with Gunicorn + Nginx

```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:9090 src.server:app
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-Q-IP $remote_addr;
    }
}
```

### Step 5: Systemd Service

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

---

## Last Updated

2026-04-08 - Migrated TTS from inline Qwen3-TTS to ComfyUI API backend; updated start_comfyui.sh for NVIDIA/AMD GPU auto-detect; added generate_harvey_tts.py standalone script