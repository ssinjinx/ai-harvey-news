#!/bin/bash
# Start ComfyUI for InfiniteTalk video generation on AMD RX 7900 XTX (ROCm)
# Run this from the ComfyUI directory: bash ~/ai-harvey-news/comfyui/start_comfyui.sh

COMFYUI_DIR="${COMFYUI_DIR:-$HOME/ComfyUI}"

export HSA_OVERRIDE_GFX_VERSION=11.0.0
export MIOPEN_FIND_MODE=2
export FLASH_ATTENTION_TRITON_AMD_ENABLE="TRUE"
export PYTORCH_ALLOC_CONF=expandable_segments:True

cd "$COMFYUI_DIR"

# Kill any existing ComfyUI instance
pkill -f "python.*main.py" 2>/dev/null && sleep 2

source venv/bin/activate

# -u = unbuffered output so logs appear immediately (important for debugging)
python3 -u main.py --use-sage-attention --listen 0.0.0.0 "$@"
