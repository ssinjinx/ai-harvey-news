#!/usr/bin/env python3
"""
Submit an InfiniteTalk video generation job to ComfyUI.

Usage:
    python submit.py                              # use defaults (harveycyborg.png + harveyclip_5s.wav)
    python submit.py --image myface.png --audio myclip.wav
    python submit.py --width 240 --height 416     # change resolution
    python submit.py --comfyui http://localhost:8188
"""

import json
import argparse
import urllib.request
import urllib.error

def submit(image, audio, width, height, comfyui_url, prefix="InfiniteTalk"):
    with open("workflow_api.json") as f:
        workflow = json.load(f)

    # Patch inputs
    workflow["73"]["inputs"]["image"] = image
    workflow["60"]["inputs"]["audio"] = audio
    workflow["74"]["inputs"]["width"] = width
    workflow["74"]["inputs"]["height"] = height
    workflow["69"]["inputs"]["width"] = width
    workflow["69"]["inputs"]["height"] = height
    workflow["61"]["inputs"]["filename_prefix"] = prefix

    payload = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{comfyui_url}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print("Submitted:", result.get("prompt_id"))
        return result.get("prompt_id")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="harveycyborg.png")
    parser.add_argument("--audio", default="harveyclip_5s.wav")
    parser.add_argument("--width", type=int, default=240)
    parser.add_argument("--height", type=int, default=416)
    parser.add_argument("--prefix", default="InfiniteTalk")
    parser.add_argument("--comfyui", default="http://127.0.0.1:8188")
    args = parser.parse_args()

    submit(args.image, args.audio, args.width, args.height, args.comfyui, args.prefix)
