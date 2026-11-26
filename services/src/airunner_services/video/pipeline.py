"""LTX pipeline backends.

RealBackend loads the diffusers LTX pipeline (lazy torch import);
Nvfp4Backend refuses to run slowly on cu129 instead of pretending.
Tests inject a fake backend — the service never needs weights.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Protocol

from airunner_services.video.config import VideoConfig
from airunner_services.video.contracts import VideoGenerationRequest
from airunner_services.video.telemetry import (
    TelemetrySampler,
    nvfp4_fast_path_available,
)

ProgressFn = Callable[[float], None]


class WeightsMissingError(RuntimeError):
    """Raised when a checkpoint directory is absent (HTTP 503)."""


class VideoResult:
    """Finished clip path plus measured telemetry."""

    def __init__(self, path: Path, wall_time_s: float,
                 peak_vram_mb: float, peak_rss_mb: float) -> None:
        self.path = path
        self.wall_time_s = wall_time_s
        self.peak_vram_mb = peak_vram_mb
        self.peak_rss_mb = peak_rss_mb


class VideoBackend(Protocol):
    """One generation backend; run() blocks until the MP4 exists."""

    def run(self, request: VideoGenerationRequest, out: Path,
            on_progress: ProgressFn) -> VideoResult:
        """Generate one clip to `out` and return its telemetry."""
        ...


class LtxDiffusersBackend:
    """Diffusers LTX pipeline with sequential offload (16 GB safe)."""

    def __init__(self, config: VideoConfig) -> None:
        self._config = config
        self._pipe = None

    def _load(self, checkpoint: str):
        ckpt = self._config.checkpoint_dir(checkpoint)
        if not ckpt.is_dir():
            raise WeightsMissingError(
                f"checkpoint not installed at {ckpt}; "
                f"run scripts/ltx_setup.sh"
            )
        if checkpoint == "nvfp4" and not nvfp4_fast_path_available():
            raise RuntimeError(
                "NVFP4 fast path needs torch cu130+; installed torch "
                "would silently fall back ~2x slower. Use fp8."
            )
        import torch
        from diffusers import DiffusionPipeline

        dtype = torch.bfloat16
        fp8_file = ckpt / "ltx-2-19b-distilled-fp8.safetensors"
        has_shards = (ckpt / "transformer").is_dir() and any(
            (ckpt / "transformer").glob("*.safetensors")
        )
        if fp8_file.is_file() and not has_shards:
            # FP8 ships as one file; the rest uses diffusers layout.
            # The repo transformer/config.json (caption_channels=3840)
            # must size the model or audio projection shapes mismatch.
            from diffusers import LTX2VideoTransformer3DModel

            cfg_path = ckpt / "transformer" / "config.json"
            extra = {"config": str(cfg_path)} if cfg_path.is_file() else {}
            # No torch_dtype: keep FP8 tensors FP8 (a BF16 upcast of
            # this 26 GB mixed file needs ~43 GB RAM and OOMs 32 GB).
            transformer = LTX2VideoTransformer3DModel.from_single_file(
                str(fp8_file), **extra
            )
            # Gemma BF16 (~24 GB) + transformer (26 GB) cannot be
            # CPU-resident together in 32 GB, so the pipeline gets a
            # weightless (meta) encoder; run() precomputes embeddings
            # in a separate phase and passes prompt_embeds instead.
            from transformers import (
                Gemma3Config,
                Gemma3ForConditionalGeneration,
            )

            with torch.device("meta"):
                empty_encoder = Gemma3ForConditionalGeneration(
                    Gemma3Config.from_pretrained(
                        str(ckpt / "text_encoder" / "config.json")
                    )
                )
            pipe = DiffusionPipeline.from_pretrained(
                str(ckpt), transformer=transformer,
                text_encoder=empty_encoder, torch_dtype=dtype,
            )
        else:
            pipe = DiffusionPipeline.from_pretrained(
                str(ckpt), torch_dtype=dtype
            )
        # Sequential offload keeps peak VRAM inside the 16 GB budget.
        pipe.enable_sequential_cpu_offload()
        pipe.vae.enable_tiling()
        self._pipe = pipe
        return pipe

    def run(self, request: VideoGenerationRequest, out: Path,
            on_progress: ProgressFn) -> VideoResult:
        """Run distilled denoising, decode, and mux via diffusers."""
        # Encode before loading the pipeline: Gemma (24 GB) and the
        # transformer (26 GB) must never be resident together.
        ckpt = self._config.checkpoint_dir(request.checkpoint)
        embeds, mask = self._encode(
            ckpt, [request.prompt, request.negative_prompt or ""]
        )
        pipe = self._pipe or self._load(request.checkpoint)
        sampler = TelemetrySampler()
        sampler.start()
        started = time.perf_counter()
        try:
            import torch

            generator = None
            if request.seed is not None:
                generator = torch.Generator("cuda").manual_seed(
                    request.seed
                )
            steps = request.steps

            def _cb(pipe_, step, timestep, callback_kwargs):
                on_progress((step + 1) / max(steps, 1))
                return callback_kwargs

            kwargs: dict = {}
            if request.input_image_path:
                from PIL import Image

                kwargs["image"] = Image.open(
                    request.input_image_path
                ).convert("RGB")
            # LTX requires multiples of 32; pad up, crop back after.
            pad_w = (request.width + 31) // 32 * 32
            pad_h = (request.height + 31) // 32 * 32
            result = pipe(
                prompt_embeds=embeds[0:1],
                negative_prompt_embeds=embeds[1:2],
                prompt_attention_mask=mask[0:1],
                negative_prompt_attention_mask=mask[1:2],
                width=pad_w, height=pad_h,
                num_frames=request.num_frames,
                frame_rate=float(request.fps),
                num_inference_steps=steps, guidance_scale=1.0,
                generator=generator,
                callback_on_step_end=_cb,
                **kwargs,
            )
            frames = result.frames[0]
            audio = getattr(result, "audio", None)
            _mux_mp4(frames, audio, request.fps, out)
        finally:
            sampler.stop()
        return VideoResult(
            out, time.perf_counter() - started,
            sampler.peak_vram_mb, sampler.peak_rss_mb,
        )

    def _encode(self, ckpt: Path, texts: list[str]):
        """Phase A: Gemma-only encoding; freed before phase B loads.

        Mirrors LTX2Pipeline.encode_prompt: hidden states stacked
        and flattened to (batch, seq, layers*dim) embeddings.
        """
        import gc

        import torch
        from transformers import (
            AutoTokenizer,
            Gemma3ForConditionalGeneration,
        )

        tokenizer = AutoTokenizer.from_pretrained(str(ckpt / "tokenizer"))
        tokenizer.padding_side = "left"
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        # Low-VRAM default: NF4 Gemma (~9 GB, fully on GPU). The BF16
        # encoder (24 GB) is only a fallback; scripts/ltx_setup.sh
        # builds the NF4 cache once (see gemma-nf4 in the models dir).
        nf4_dir = ckpt.parent / "gemma-nf4"
        if nf4_dir.is_dir():
            from transformers import BitsAndBytesConfig

            model = Gemma3ForConditionalGeneration.from_pretrained(
                str(nf4_dir),
                quantization_config=BitsAndBytesConfig(
                    load_in_4bit=True, bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                ),
                device_map="cuda", low_cpu_mem_usage=True,
            )
        else:
            model = Gemma3ForConditionalGeneration.from_pretrained(
                str(ckpt / "text_encoder"),
                torch_dtype=torch.bfloat16, device_map="auto",
                max_memory={0: "11GiB", "cpu": "16GiB"},
                low_cpu_mem_usage=True,
            )
        try:
            inputs = tokenizer(
                texts, padding="max_length", max_length=1024,
                truncation=True, add_special_tokens=True,
                return_tensors="pt",
            )
            with torch.no_grad():
                outputs = model(
                    input_ids=inputs.input_ids,
                    attention_mask=inputs.attention_mask,
                    output_hidden_states=True,
                )
            hidden = torch.stack(outputs.hidden_states, dim=-1)
            embeds = hidden.flatten(2, 3).to(torch.bfloat16)
            return embeds, inputs.attention_mask
        finally:
            del model
            gc.collect()

    def unload(self) -> None:
        """Free the pipeline (idle unload)."""
        self._pipe = None
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass


def _mux_mp4(frames, audio, fps: int, out: Path) -> None:
    """Write frames (+ joint audio when present) to MP4 via ffmpeg."""
    import subprocess

    import numpy as np
    from PIL import Image

    frames_dir = out.parent / f"{out.stem}-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        array = np.asarray(frame)
        Image.fromarray(array).save(frames_dir / f"{index:05d}.png")
    cmd = ["ffmpeg", "-y", "-framerate", str(fps),
           "-i", str(frames_dir / "%05d.png")]
    if audio is not None:
        wav = out.with_suffix(".wav")
        import soundfile as sf

        sf.write(str(wav), audio, samplerate=24000)
        cmd += ["-i", str(wav), "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(out)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
