#!/usr/bin/env bash
# Install LTX weights + verify the local stack. Idempotent.
# Direct track (daemon): Lightricks/LTX-2 diffusers FP8 layout.
# ComfyUI track (--comfyui): LTX-2.3 22B checkpoints. Weights never in git.
# License: LTX-2 License (free < $10M revenue; commercial above).
set -euo pipefail

MODELS_DIR="${AIRUNNER_VIDEO_MODELS_DIR:-$HOME/.local/share/airunner/models/video}"
FP8_DIR="$MODELS_DIR/ltx-2.3-fp8"
PY="${AIRUNNER_PYTHON:-.venv/bin/python}"

echo "== Host check =="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
"$PY" -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
ffmpeg -version | head -1

echo "== Direct track: Lightricks/LTX-2 distilled FP8 (diffusers) =="
mkdir -p "$FP8_DIR"
MODELS_DIR="$MODELS_DIR" "$PY" - <<'PYEOF'
import os
from huggingface_hub import snapshot_download
base = os.path.expanduser(os.environ["MODELS_DIR"])
snapshot_download(
    "Lightricks/LTX-2",
    local_dir=base + "/ltx-2.3-fp8",
    # text_encoder ships two serializations (~50 GB each); keep the
    # transformers Gemma set only, or the subset balloons to ~133 GB.
    allow_patterns=[
        "ltx-2-19b-distilled-fp8.safetensors",
        "text_encoder/model-*", "text_encoder/config.json",
        "text_encoder/generation_config.json",
        "text_encoder/model.safetensors.index.json",
        "transformer/config.json",
        "tokenizer/*", "vae/*",
        "audio_vae/*", "vocoder/*", "scheduler/*",
        "connectors/*", "model_index.json",
    ],
)
print("direct track installed")
PYEOF

echo "== Manifest (reproducibility) =="
(cd "$FP8_DIR" && find . -type f -exec sha256sum {} + | sort -k2 > MANIFEST.sha256)
wc -l "$FP8_DIR/MANIFEST.sha256"

if [[ "${1:-}" == "--comfyui" ]]; then
  echo "== ComfyUI track: LTX-2.3 22B + Gemma FP4 encoder (:8189) =="
  COMFY="$HOME/.local/share/airunner/comfyui"
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$COMFY" 2>/dev/null || true
  git -C "$COMFY/custom_nodes" clone --depth 1 https://github.com/Lightricks/ComfyUI-LTXVideo 2>/dev/null || true
  MODELS_DIR="$MODELS_DIR" "$PY" - <<'PYEOF'
import os
from huggingface_hub import hf_hub_download
base = os.path.expanduser(os.environ["MODELS_DIR"])
hf_hub_download("protoLabsAI/LTX-2.3-22B-distilled-NVFP4",
                "ltx-2.3-22b-distilled-1.1-fp4.safetensors",
                local_dir=base + "/ltx-2.3-nvfp4")
hf_hub_download("Comfy-Org/LTX-2",
                "split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors",
                local_dir=base + "/ltx-2.3-nvfp4")
print("comfyui track installed (NVFP4 needs cu130 fast path)")
PYEOF
fi

echo "Done. Start: airunner-daemon  |  API: POST /api/v1/video/generate"
echo "Benchmark: $PY scripts/ltx_benchmark.py"
