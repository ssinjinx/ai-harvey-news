#!/bin/bash
# Daily Harvey News Pipeline
# Runs at 10 PM: scrape -> LLM rewrite -> TTS top 5 -> cleanup old
#
# Prerequisites:
#   1. ComfyUI running at http://localhost:8188
#   2. Ollama running locally
#   3. Reference audio in ComfyUI input dir (harveyclip_5s.wav)
#
# Crontab entry:
#   0 22 * * * /home/ssinjin/projects/ai-harvey-news/daily_pipeline.sh >> /home/ssinjin/projects/ai-harvey-news/data/pipeline.log 2>&1

set -euo pipefail

PROJECT_DIR="/home/ssinjin/projects/ai-harvey-news"
VENV="$PROJECT_DIR/venv"
DATA_DIR="$PROJECT_DIR/data"
COMFYUI_URL="http://localhost:8188"
LOG_DIR="$DATA_DIR"
LOGFILE="$LOG_DIR/pipeline.log"

mkdir -p "$DATA_DIR" "$LOG_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

# ── Pre-flight checks ──────────────────────────────────────────────
log "=== Starting daily pipeline ==="

# Activate venv
source "$VENV/bin/activate"

# Check ComfyUI is up (TTS depends on it)
if ! curl -sf "$COMFYUI_URL/system_stats" > /dev/null 2>&1; then
    log "ERROR: ComfyUI not reachable at $COMFYUI_URL — starting it..."
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}
    COMFYUI_DIR="/media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI"
    cd "$COMFYUI_DIR"
    nohup ./venv/bin/python main.py --listen 0.0.0.0 > /tmp/comfyui_pipeline.log 2>&1 &
    COMFYUI_PID=$!
    log "ComfyUI starting (PID: $COMFYUI_PID), waiting 30s..."
    sleep 30
    if curl -sf "$COMFYUI_URL/system_stats" > /dev/null 2>&1; then
        log "ComfyUI is up"
    else
        log "ERROR: ComfyUI failed to start. Aborting."
        exit 1
    fi
fi

# Check Ollama is up
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    log "ERROR: Ollama not reachable at localhost:11434 — aborting."
    exit 1
fi
log "Ollama is up"

# Set data directory (use local project dir, not remote server path)
export HARVEY_DATA_DIR="$DATA_DIR"
export COMFYUI_URL="$COMFYUI_URL"
export COMFYUI_DIR="/media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI"

cd "$PROJECT_DIR"

# ── Pipeline steps ──────────────────────────────────────────────────

# 1. Scrape new articles
log "Scraping news with LLM summarization..."
python main.py scrape --llm >> "$LOGFILE" 2>&1 || log "WARNING: Scrape step had errors"

# 2. Fetch full article content
log "Fetching article content..."
python main.py fetch-content >> "$LOGFILE" 2>&1 || log "WARNING: Fetch-content step had errors"

# 3. Generate audio for top articles (uses ComfyUI Qwen3-TTS)
log "Generating Harvey audio via ComfyUI (this takes a while)..."
python main.py generate-audio --limit 5 >> "$LOGFILE" 2>&1 || log "WARNING: Audio generation had errors"

# 4. Cleanup old audio files (keep last 3 days)
log "Cleaning up audio cache older than 3 days..."
find "$DATA_DIR/audio_cache" -name "*.wav" -mtime +3 -delete 2>/dev/null || true
find "$DATA_DIR/audio_cache" -name "*_script.txt" -mtime +3 -delete 2>/dev/null || true

log "=== Pipeline complete ==="
echo "---" >> "$LOGFILE"