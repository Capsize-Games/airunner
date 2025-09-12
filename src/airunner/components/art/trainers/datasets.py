"""Dataset utilities for image+caption training.

Provides a simple folder-based dataset with optional sidecar captions and
JSONL metadata, plus configurable resize/crop/pad transforms.
"""

import json
import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms


IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class FolderWithCaptions(Dataset):
    """Folder dataset with optional captions.

    Reads images from a directory and captions from one of the following:
    - Sidecar JSON named `<image>.json` containing the key given by
      `caption_key` (defaults to "text"; "caption" is also accepted), or
    - A `captions.jsonl` file at the root with records
      `{ "file": "img.jpg", "text": "..." }`, or
    - Falls back to the filename stem when no caption is provided.

    Transforms support two strategies:
    - resize_mode == "crop": Resize the shorter side to `resolution` and
      optionally CenterCrop.
    - resize_mode == "pad": Pad to square using `pad_color` then resize.
    """

    image_dir: str
    resolution: int
    center_crop: bool = False
    random_flip: bool = False
    caption_key: str = "text"
    resize_mode: str = "crop"  # crop|pad
    pad_color: Tuple[int, int, int] = (255, 255, 255)

    def __post_init__(self) -> None:
        # Build file list and optional captions
        self._items: List[Tuple[str, Optional[str]]] = []
        for fname in sorted(os.listdir(self.image_dir)):
            fpath = os.path.join(self.image_dir, fname)
            root, ext = os.path.splitext(fname)
            if not os.path.isfile(fpath) or ext.lower() not in IMG_EXTS:
                continue
            caption: Optional[str] = None
            sidecar = os.path.join(self.image_dir, f"{root}.json")
            if os.path.exists(sidecar):
                try:
                    with open(sidecar, "r", encoding="utf-8") as fp:
                        meta = json.load(fp)
                        caption = meta.get(self.caption_key) or meta.get(
                            "caption"
                        )
                except Exception:
                    caption = None
            self._items.append((fpath, caption))

        # Optional captions.jsonl mapping
        cap_jsonl = os.path.join(self.image_dir, "captions.jsonl")
        if os.path.exists(cap_jsonl):
            mapping: Dict[str, str] = {}
            with open(cap_jsonl, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        fname = rec.get("file", "")
                        if not fname:
                            continue
                        text = rec.get(self.caption_key, rec.get("caption"))
                        if text is not None:
                            mapping[fname] = text
                    except Exception:
                        continue
            new_items: List[Tuple[str, Optional[str]]] = []
            for fpath, cap in self._items:
                base = os.path.basename(fpath)
                new_items.append((fpath, mapping.get(base, cap)))
            self._items = new_items

        # Build transforms
        tfms: List[Callable] = []
        if self.resize_mode == "pad":
            # Pad to square keeping aspect ratio, then resize
            def pad_to_square(img: Image.Image) -> Image.Image:
                w, h = img.size
                if w == h:
                    return img
                side = max(w, h)
                new_img = Image.new("RGB", (side, side), color=self.pad_color)
                offset = ((side - w) // 2, (side - h) // 2)
                new_img.paste(img, offset)
                return new_img

            tfms.append(pad_to_square)
            tfms.append(
                transforms.Resize(
                    (self.resolution, self.resolution),
                    interpolation=Image.BICUBIC,
                )
            )
        else:
            # Default: resize and (optionally) center-crop
            tfms.append(
                transforms.Resize(self.resolution, interpolation=Image.BICUBIC)
            )
            if self.center_crop:
                tfms.append(transforms.CenterCrop(self.resolution))
        if self.random_flip:
            tfms.append(transforms.RandomHorizontalFlip())
        tfms.append(transforms.ToTensor())
        # Normalize to [-1,1] as expected by SD
        tfms.append(transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]))
        self._transform = transforms.Compose(tfms)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, idx: int):
        path, caption = self._items[idx]
        image = Image.open(path).convert("RGB")
        pixel_values = self._transform(image)
        if caption is None:
            caption = os.path.splitext(os.path.basename(path))[0]
        return {"pixel_values": pixel_values, "caption": caption}
