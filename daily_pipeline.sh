#!/bin/bash
# Daily Harvey News Pipeline
# Runs at 10pm: scrape -> LLM rewrite -> TTS top 5 -> cleanup old

export HARVEY_DATA_DIR=/opt/ai-harvey-news/data
export PATH="/opt/ai-harvey-news/venv/bin:$PATH"

cd /opt/ai-harvey-news

LOGFILE="/var/log/harvey-pipeline.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

log "=== Starting daily pipeline ==="

# 1. Scrape new articles
log "Scraping news..."
python main.py scrape --llm >> "$LOGFILE" 2>&1

# 2. Fetch full content
log "Fetching article content..."
python main.py fetch-content >> "$LOGFILE" 2>&1

# 3. Generate audio for top 5 articles
log "Generating AI-Harvey audio for top 5..."
python main.py generate-audio --limit 5 >> "$LOGFILE" 2>&1

# 4. Cleanup old audio files (keep today's, delete yesterday's)
log "Cleaning up old audio files..."
find "$HARVEY_DATA_DIR/audio_cache" -name "*.wav" -mtime +1 -delete 2>/dev/null
find "$HARVEY_DATA_DIR/audio_cache" -name "*_script.txt" -mtime +1 -delete 2>/dev/null

log "=== Pipeline complete ==="
echo "---" >> "$LOGFILE"