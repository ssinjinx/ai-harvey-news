#!/bin/bash
# Start ComfyUI for TTS and video generation
# Auto-detects NVIDIA vs AMD GPU and sets appropriate env vars
#
# Usage:
#   bash start_comfyui.sh                    # auto-detect GPU
#   COMFYUI_DIR=/path/to/ComfyUI bash start_comfyui.sh

COMFYUI_DIR="${COMFYUI_DIR:-/media/ssinjin/c173cbdc-b600-4f53-8185-b87fbce0bc3b/ComfyUI}"

# Kill any existing ComfyUI instance
pkill -f "python.*main.py.*8188" 2>/dev/null && sleep 2

# Detect GPU type
if nvidia-smi &>/dev/null; then
    echo "🖥️  NVIDIA GPU detected"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}
    GPU_ARGS=""
elif [ -d /opt/rocm ] || [ -f /sys/class/drm/card*/device/vendor ] && grep -q "1002" /sys/class/drm/card*/device/vendor 2>/dev/null; then
    echo "🖥️  AMD GPU detected (ROCm)"
    export HSA_OVERRIDE_GFX_VERSION=11.0.0
    export MIOPEN_FIND_MODE=2
    export FLASH_ATTENTION_TRITON_AMD_ENABLE="TRUE"
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    GPU_ARGS="--use-sage-attention"
else
    echo "⚠️  No GPU detected, running on CPU (will be slow)"
    GPU_ARGS=""
fi

cd "$COMFYUI_DIR"

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "🚀 Starting ComfyUI at http://localhost:8188 ..."
# -u = unbuffered output so logs appear immediately
python3 -u main.py --listen 0.0.0.0 $GPU_ARGS "$@"