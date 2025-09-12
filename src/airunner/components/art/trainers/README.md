# Art Trainers (Diffusers)

Trainer classes to fine-tune Stable Diffusion models locally:

- SDTextToImageTrainer: UNet fine-tuning on a folder of images+captions.
- SDLoRATrainer: LoRA training targeting UNet attention processors and optionally the text encoder.
- TextualInversionTrainer: Learn a placeholder token embedding from a few images.

Features
- Local model path input; no network required after weights are present.
- Folder-based dataset loader supporting sidecar captions (`<image>.json`), a `captions.jsonl`, or filename-as-caption.
- Minimal dependencies: diffusers, transformers, torch, accelerate (installed by the project).
- Works as importable classes or via a CLI.

Install requirements
- If you installed AI Runner without extras, install training deps:
  pip install "airunner[huggingface]"

CLI
Use the console script installed by the package:

- Finetune UNet
  airunner-train-diffusers finetune \
    --pretrained_model_path "/path/to/sd15" \
    --train_data_dir "/path/to/images" \
    --output_dir "/path/to/out" \
    --resolution 512 --train_batch_size 1 --max_train_steps 1000
  # add --logging_steps 20 to print progress every 20 steps

- Train LoRA
  airunner-train-diffusers lora \
  --pretrained_model_path "/path/to/sd15" \
    --train_data_dir "/path/to/images" \
    --output_dir "/path/to/out" \
    --resolution 512 --train_batch_size 1 --max_train_steps 2000 \
    --lora_rank 8 --lora_alpha 32
  # add --logging_steps 20 to print progress every 20 steps

- Train Textual Inversion
  airunner-train-diffusers textual-inversion \
    --pretrained_model_path "/path/to/sd15" \
    --train_data_dir "/path/to/images" \
    --output_dir "/path/to/out" \
    --placeholder_token "<my-token>" --initializer_token "toy" \
    --resolution 512 --train_batch_size 1 --max_train_steps 1500
  # add --logging_steps 20 to print progress every 20 steps

Import in GUI threads
from airunner.components.art.trainers import TrainingConfig, SDLoRATrainer

cfg = TrainingConfig(
    pretrained_model_path="/models/sd15",
    train_data_dir="/data/myset",
    output_dir="/runs/lora-001",
)
trainer = SDLoRATrainer(cfg)
# Run trainer in a background thread managed by WorkerManager
trainer.train()

Notes
- These scripts are simplified and inspired by the official diffusers examples:
  - text_to_image: https://github.com/huggingface/diffusers/tree/main/examples/text_to_image
  - textual_inversion: https://github.com/huggingface/diffusers/tree/main/examples/textual_inversion
- For best results, consider enabling xFormers and PyTorch 2.x scaled-dot-product attention.
- Outputs: one final `.safetensors` file is written at the root of `output_dir` (no `final/` folder). Optional `checkpoint-*/` directories may be created during training and are cleaned up automatically at the end.
 - Live progress: a tqdm progress bar is shown during training; you can also use `--logging_steps N` for periodic logs.
 - Important: `--pretrained_model_path` must point to a Diffusers model directory (e.g., contains `tokenizer/`, `text_encoder/`, `unet/`, `vae/`, `scheduler/`). If you have a single `.safetensors` or `.ckpt`, first convert it to Diffusers format or use an existing Diffusers SD/SDXL model folder.

## Dataset guidelines and trigger words

Recommended images
- Content: Clear subjects that represent what you want the model to learn (object, style, person). Avoid busy backgrounds.
- Variety: 10–30 images (SD 1.x) or 20–50 images (SDXL) with diverse viewpoints, lighting, and backgrounds to prevent overfitting.
- Resolution: 512–768 for SD 1.x, 768–1024 for SDXL. The trainer will resize to `--resolution`.
- Quality: Sharp, well-exposed images; avoid heavy compression and watermarks.

Captions and trigger words
- Provide concise captions describing the main subject and context.
- Use a unique trigger word (or phrase) that doesn’t appear elsewhere in your dataset (e.g., `skscar` or `vgsbrandx`).
- Multiple trigger words are supported and can be combined into a phrase.

Using trigger words via CLI
- Prepend (default):
  airunner-train-diffusers finetune ... --trigger_word mytoken
- Append:
  airunner-train-diffusers lora ... --trigger_word mytoken --trigger_mode append
- Replace captions entirely:
  airunner-train-diffusers textual-inversion ... --trigger_word "mytoken style" --trigger_mode replace

How triggers are applied
- finetune/lora: Triggers are merged with the caption(s) per `--trigger_mode`.
- textual-inversion: The placeholder token you specify still defines the learned embedding; triggers are applied in addition to captions to strengthen association.

Suggested counts
- Finetune (object/style): SD 1.x → 20–100 images; SDXL → 40–200 images.
- LoRA (style/lightweight concept): SD 1.x → 10–50 images; SDXL → 20–100 images.
- Textual inversion (single concept): SD 1.x → 5–20 images; SDXL → 10–40 images.

Picking a placeholder token (textual inversion)
- Choose a unique token like `<mytoken>` and set `--placeholder_token "<mytoken>"`.
- Set `--initializer_token` to a semantically related word (e.g., `toy`, `style`, `person`) to provide a good starting embedding.
- For SDXL, the trainer learns embeddings for both encoders; both files will be saved and should be loaded at inference.