#!/usr/bin/env python3
"""
HuggingFace model download utility for AI Runner.

Download models from HuggingFace directly from the command line,
similar to `ollama pull`.

Usage:
    airunner-hf-download                    # List all available models
    airunner-hf-download list               # List all available models
    airunner-hf-download list --type llm    # List only LLM models
    airunner-hf-download qwen3-8b           # Download GGUF variant (default)
    airunner-hf-download --full qwen3-8b    # Download full safetensors
    airunner-hf-download Qwen/Qwen3-8B      # Download by repo_id
    airunner-hf-download --downloaded       # List downloaded models
    airunner-hf-download --delete <model>   # Delete a downloaded model

Examples:
    # List all available models
    airunner-hf-download

    # Download Qwen3 8B model (GGUF by default - smaller/faster)
    airunner-hf-download qwen3-8b

    # Download full safetensors version (larger but higher precision)
    airunner-hf-download --full qwen3-8b

    # Download Qwen3 Coder (14.7GB GGUF fits in 16GB VRAM)
    airunner-hf-download qwen3-coder-30b-a3b

    # Download any HuggingFace model by repo ID
    airunner-hf-download meta-llama/Llama-3.1-8B-Instruct

    # List downloaded models
    airunner-hf-download --downloaded

    # Delete a model
    airunner-hf-download --delete Qwen3-8B
"""

import argparse
import os
import sys
import threading
from typing import Dict, List, Optional, Tuple


def get_all_available_models() -> Dict[str, List[Dict]]:
    """Get all available models organized by type.
    
    Returns:
        Dictionary with model types as keys and lists of model info as values
    """
    models = {
        "llm": [],
        "art": [],
        "tts": [],
        "stt": [],
        "embedding": [],
    }
    
    # Get LLM models from provider config
    try:
        from airunner.components.llm.config.provider_config import LLMProviderConfig
        for model_key, info in LLMProviderConfig.LOCAL_MODELS.items():
            if model_key == "custom":
                continue
            models["llm"].append({
                "key": model_key,
                "name": info.get("name", model_key),
                "repo_id": info.get("repo_id", ""),
                "description": info.get("description", ""),
                "vram_4bit": info.get("vram_4bit_gb", 0),
                "context_length": info.get("context_length", 0),
                "has_gguf": bool(info.get("gguf_repo_id")),
                "gguf_repo_id": info.get("gguf_repo_id", ""),
                "gguf_filename": info.get("gguf_filename", ""),
                "type": "llm",
            })
    except ImportError:
        pass
    
    # Get art models from bootstrap data
    try:
        from airunner.components.data.bootstrap.model_bootstrap_data import ai_art_models
        for model in ai_art_models:
            models["art"].append({
                "key": model["name"].lower().replace(" ", "-"),
                "name": model["name"],
                "repo_id": model["path"],
                "description": f"{model['version']} - {model['pipeline_action']}",
                "vram_4bit": 0,
                "context_length": 0,
                "has_gguf": False,
                "type": "art",
                "pipeline_action": model.get("pipeline_action", "txt2img"),
                "version": model.get("version", ""),
            })
    except ImportError:
        pass
    
    # Get TTS models from OpenVoice bootstrap
    try:
        from airunner.components.tts.data.bootstrap.openvoice_bootstrap_data import OPENVOICE_FILES
        for repo_id in OPENVOICE_FILES.keys():
            name = repo_id.split("/")[-1]
            models["tts"].append({
                "key": name.lower(),
                "name": name,
                "repo_id": repo_id,
                "description": "TTS model for OpenVoice",
                "vram_4bit": 0,
                "context_length": 0,
                "has_gguf": False,
                "type": "tts",
            })
    except ImportError:
        pass
    
    # Get STT models from Whisper bootstrap
    try:
        from airunner.components.stt.data.bootstrap.whisper import WHISPER_FILES
        for repo_id in WHISPER_FILES.keys():
            name = repo_id.split("/")[-1]
            models["stt"].append({
                "key": name.lower(),
                "name": name,
                "repo_id": repo_id,
                "description": "Speech-to-text model (Whisper)",
                "vram_4bit": 2,
                "context_length": 0,
                "has_gguf": False,
                "type": "stt",
            })
    except ImportError:
        pass
    
    # Get embedding models from bootstrap data
    try:
        from airunner.components.data.bootstrap.model_bootstrap_data import llm_models
        for model in llm_models:
            if model.get("pipeline_action") == "embedding":
                models["embedding"].append({
                    "key": model["name"].lower().replace(" ", "-"),
                    "name": model["name"],
                    "repo_id": model["path"],
                    "description": "Embedding model for RAG",
                    "vram_4bit": 1,
                    "context_length": 0,
                    "has_gguf": False,
                    "type": "embedding",
                })
    except ImportError:
        pass
    
    return models


def find_model(identifier: str, models: Dict[str, List[Dict]]) -> Optional[Dict]:
    """Find a model by key or repo_id.
    
    Args:
        identifier: Model key (e.g., 'qwen3-8b') or repo_id (e.g., 'Qwen/Qwen3-8B')
        models: Dictionary of all available models
        
    Returns:
        Model info dict if found, None otherwise
    """
    identifier_lower = identifier.lower()
    
    # Search all model types
    for model_type, model_list in models.items():
        for model in model_list:
            # Match by key
            if model["key"].lower() == identifier_lower:
                return model
            # Match by repo_id (case-insensitive)
            if model["repo_id"].lower() == identifier_lower:
                return model
            # Match by name
            if model["name"].lower() == identifier_lower:
                return model
    
    return None


def print_model_list(models: Dict[str, List[Dict]], model_type: Optional[str] = None):
    """Print available models in a formatted list.
    
    Args:
        models: Dictionary of all available models
        model_type: Optional filter by model type
    """
    type_colors = {
        "llm": "\033[94m",      # Blue
        "art": "\033[95m",      # Magenta
        "tts": "\033[93m",      # Yellow
        "stt": "\033[92m",      # Green
        "embedding": "\033[96m", # Cyan
    }
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    
    print(f"\n{bold}Available Models{reset}")
    print("=" * 80)
    print(f"{dim}Use 'airunner-hf-download <model>' to download (GGUF by default){reset}")
    print(f"{dim}Use 'airunner-hf-download --full <model>' for full safetensors{reset}\n")
    
    types_to_show = [model_type] if model_type else ["llm", "art", "tts", "stt", "embedding"]
    
    for mtype in types_to_show:
        if mtype not in models or not models[mtype]:
            continue
            
        color = type_colors.get(mtype, "")
        print(f"{bold}{color}[{mtype.upper()}]{reset}")
        print("-" * 40)
        
        for model in models[mtype]:
            gguf_indicator = " [GGUF]" if model.get("has_gguf") else ""
            
            # Build VRAM info string
            vram_info = ""
            if model.get("vram_4bit"):
                vram_info = f"VRAM: {model['vram_4bit']}GB (4-bit)"
            
            # Build context length string
            ctx_info = ""
            if model.get("context_length"):
                ctx_k = model['context_length'] // 1000
                ctx_info = f"Context: {ctx_k}K"
            
            print(f"  {bold}{model['key']}{reset}{gguf_indicator}")
            print(f"    {dim}Repo: {model['repo_id']}{reset}")
            
            # Print specs on one line if available
            specs = []
            if vram_info:
                specs.append(vram_info)
            if ctx_info:
                specs.append(ctx_info)
            if specs:
                print(f"    {dim}{' | '.join(specs)}{reset}")
            
            if model.get("description"):
                print(f"    {dim}{model['description']}{reset}")
            print()
        
        print()


def download_model(
    model_info: Dict,
    use_gguf: bool = True,  # Default to GGUF for LLMs
    output_dir: Optional[str] = None,
) -> bool:
    """Download a model using huggingface_hub with tqdm progress.
    
    Args:
        model_info: Model information dictionary
        use_gguf: Whether to download GGUF variant (default True for LLMs)
        output_dir: Optional output directory override
        
    Returns:
        True if download succeeded, False otherwise
    """
    from huggingface_hub import hf_hub_download, snapshot_download
    from huggingface_hub.utils import HfHubHTTPError
    
    model_type = model_info.get("type", "llm")
    repo_id = model_info["repo_id"]
    model_name = model_info["name"]
    
    # For LLMs, prefer GGUF by default if available
    gguf_filename = None
    if model_type == "llm" and use_gguf and model_info.get("has_gguf"):
        repo_id = model_info["gguf_repo_id"]
        gguf_filename = model_info["gguf_filename"]
        model_name = f"{model_name} (GGUF: {gguf_filename})"
    elif model_type == "llm" and use_gguf and not model_info.get("has_gguf"):
        print(f"\n⚠️  Model '{model_name}' does not have a GGUF variant, downloading full model...")
    
    # Determine output directory
    if output_dir is None:
        from airunner.settings import MODELS_DIR
        if model_type == "llm":
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")
        elif model_type == "art":
            output_dir = os.path.join(MODELS_DIR, "art/models")
        elif model_type == "tts":
            output_dir = os.path.join(MODELS_DIR, "text/models/tts")
        elif model_type == "stt":
            output_dir = os.path.join(MODELS_DIR, "text/models/stt")
        elif model_type == "embedding":
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/embedding")
        else:
            output_dir = os.path.join(MODELS_DIR, "models")
    
    # Create model subdirectory
    model_output_dir = os.path.join(output_dir, model_info["name"])
    os.makedirs(model_output_dir, exist_ok=True)
    
    print(f"\n📦 Downloading: {model_name}")
    print(f"   Repository: {repo_id}")
    print(f"   Destination: {model_output_dir}")
    if gguf_filename:
        print(f"   GGUF File: {gguf_filename}")
    print()
    
    try:
        if gguf_filename:
            # Download single GGUF file with progress
            print(f"⬇️  Downloading {gguf_filename}...")
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=gguf_filename,
                local_dir=model_output_dir,
                local_dir_use_symlinks=False,
            )
            print(f"\n✅ Successfully downloaded: {model_name}")
            print(f"   Saved to: {downloaded_path}")
            return True
        else:
            # Download full repository with progress
            print(f"⬇️  Downloading full repository...")
            downloaded_path = snapshot_download(
                repo_id=repo_id,
                local_dir=model_output_dir,
                local_dir_use_symlinks=False,
            )
            print(f"\n✅ Successfully downloaded: {model_name}")
            print(f"   Saved to: {downloaded_path}")
            return True
            
    except HfHubHTTPError as e:
        if "401" in str(e) or "Unauthorized" in str(e):
            print(f"\n❌ Error: Unauthorized access to {repo_id}")
            print(f"   This model may require authentication or may not exist.")
            print(f"   Try: huggingface-cli login")
        elif "404" in str(e) or "Not Found" in str(e):
            print(f"\n❌ Error: Repository not found: {repo_id}")
            if gguf_filename:
                print(f"   Or file not found: {gguf_filename}")
        else:
            print(f"\n❌ Error downloading: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        return False


def download_arbitrary_repo(repo_id: str, model_type: str = "llm") -> bool:
    """Download an arbitrary HuggingFace repository.
    
    Args:
        repo_id: HuggingFace repository ID (e.g., 'user/model')
        model_type: Type of model ('llm', 'art', 'tts', 'stt')
        
    Returns:
        True if download succeeded, False otherwise
    """
    model_info = {
        "key": repo_id.split("/")[-1].lower(),
        "name": repo_id.split("/")[-1],
        "repo_id": repo_id,
        "description": f"Custom {model_type} model",
        "vram_4bit": 0,
        "context_length": 0,
        "has_gguf": False,
        "type": model_type,
    }
    
    # For arbitrary repos, we don't have GGUF info, so download full
    return download_model(model_info, use_gguf=False)


def get_downloaded_models() -> Dict[str, List[Dict]]:
    """Get all downloaded models organized by type.
    
    Returns:
        Dictionary with model types as keys and lists of downloaded model info as values
    """
    from airunner.settings import MODELS_DIR
    
    downloaded = {
        "llm": [],
        "art": [],
        "tts": [],
        "stt": [],
        "embedding": [],
    }
    
    # Check LLM models
    llm_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")
    if os.path.exists(llm_dir):
        for name in os.listdir(llm_dir):
            model_path = os.path.join(llm_dir, name)
            if os.path.isdir(model_path):
                # Check for GGUF files
                gguf_files = [f for f in os.listdir(model_path) if f.endswith('.gguf')]
                safetensor_files = [f for f in os.listdir(model_path) if f.endswith('.safetensors')]
                
                # Calculate size
                size_bytes = sum(
                    os.path.getsize(os.path.join(model_path, f))
                    for f in os.listdir(model_path)
                    if os.path.isfile(os.path.join(model_path, f))
                )
                size_gb = size_bytes / (1024 ** 3)
                
                model_type = "GGUF" if gguf_files else ("Safetensors" if safetensor_files else "Unknown")
                downloaded["llm"].append({
                    "name": name,
                    "path": model_path,
                    "size_gb": size_gb,
                    "format": model_type,
                    "files": len(os.listdir(model_path)),
                })
    
    # Check embedding models
    embed_dir = os.path.join(MODELS_DIR, "text/models/llm/embedding")
    if os.path.exists(embed_dir):
        for name in os.listdir(embed_dir):
            model_path = os.path.join(embed_dir, name)
            if os.path.isdir(model_path):
                size_bytes = sum(
                    os.path.getsize(os.path.join(model_path, f))
                    for f in os.listdir(model_path)
                    if os.path.isfile(os.path.join(model_path, f))
                )
                size_gb = size_bytes / (1024 ** 3)
                downloaded["embedding"].append({
                    "name": name,
                    "path": model_path,
                    "size_gb": size_gb,
                    "format": "Safetensors",
                    "files": len(os.listdir(model_path)),
                })
    
    # Check art models
    art_dir = os.path.join(MODELS_DIR, "art/models")
    if os.path.exists(art_dir):
        for name in os.listdir(art_dir):
            model_path = os.path.join(art_dir, name)
            if os.path.isdir(model_path):
                size_bytes = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, _, files in os.walk(model_path)
                    for f in files
                )
                size_gb = size_bytes / (1024 ** 3)
                downloaded["art"].append({
                    "name": name,
                    "path": model_path,
                    "size_gb": size_gb,
                    "format": "Diffusion",
                    "files": sum(len(files) for _, _, files in os.walk(model_path)),
                })
    
    # Check TTS models
    tts_dir = os.path.join(MODELS_DIR, "text/models/tts")
    if os.path.exists(tts_dir):
        for name in os.listdir(tts_dir):
            model_path = os.path.join(tts_dir, name)
            if os.path.isdir(model_path):
                size_bytes = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, _, files in os.walk(model_path)
                    for f in files
                )
                size_gb = size_bytes / (1024 ** 3)
                downloaded["tts"].append({
                    "name": name,
                    "path": model_path,
                    "size_gb": size_gb,
                    "format": "TTS",
                    "files": sum(len(files) for _, _, files in os.walk(model_path)),
                })
    
    # Check STT models
    stt_dir = os.path.join(MODELS_DIR, "text/models/stt")
    if os.path.exists(stt_dir):
        for name in os.listdir(stt_dir):
            model_path = os.path.join(stt_dir, name)
            if os.path.isdir(model_path):
                size_bytes = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, _, files in os.walk(model_path)
                    for f in files
                )
                size_gb = size_bytes / (1024 ** 3)
                downloaded["stt"].append({
                    "name": name,
                    "path": model_path,
                    "size_gb": size_gb,
                    "format": "Whisper",
                    "files": sum(len(files) for _, _, files in os.walk(model_path)),
                })
    
    return downloaded


def print_downloaded_models(downloaded: Dict[str, List[Dict]], model_type: Optional[str] = None):
    """Print downloaded models in a formatted list.
    
    Args:
        downloaded: Dictionary of downloaded models
        model_type: Optional filter by model type
    """
    type_colors = {
        "llm": "\033[94m",      # Blue
        "art": "\033[95m",      # Magenta
        "tts": "\033[93m",      # Yellow
        "stt": "\033[92m",      # Green
        "embedding": "\033[96m", # Cyan
    }
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    green = "\033[92m"
    
    total_size = 0
    total_models = 0
    
    print(f"\n{bold}Downloaded Models{reset}")
    print("=" * 80)
    print(f"{dim}Use 'airunner-hf-download --delete <model>' to remove a model{reset}\n")
    
    types_to_show = [model_type] if model_type else ["llm", "art", "tts", "stt", "embedding"]
    
    for mtype in types_to_show:
        if mtype not in downloaded or not downloaded[mtype]:
            continue
            
        color = type_colors.get(mtype, "")
        print(f"{bold}{color}[{mtype.upper()}]{reset}")
        print("-" * 40)
        
        for model in downloaded[mtype]:
            size_str = f"{model['size_gb']:.1f}GB"
            total_size += model['size_gb']
            total_models += 1
            
            print(f"  {bold}{green}✓{reset} {bold}{model['name']}{reset}")
            print(f"    {dim}Size: {size_str} | Format: {model['format']} | Files: {model['files']}{reset}")
            print(f"    {dim}Path: {model['path']}{reset}")
            print()
        
        print()
    
    if total_models == 0:
        print(f"  {dim}No models downloaded yet.{reset}")
        print(f"  {dim}Use 'airunner-hf-download <model>' to download one.{reset}\n")
    else:
        print(f"{bold}Total: {total_models} model(s), {total_size:.1f}GB{reset}\n")


def delete_model(model_name: str, force: bool = False) -> bool:
    """Delete a downloaded model.
    
    Args:
        model_name: Name of the model to delete
        force: If True, skip confirmation prompt
        
    Returns:
        True if deletion succeeded, False otherwise
    """
    import shutil
    
    downloaded = get_downloaded_models()
    
    # Find the model
    found_model = None
    found_type = None
    
    for mtype, model_list in downloaded.items():
        for model in model_list:
            if model["name"].lower() == model_name.lower():
                found_model = model
                found_type = mtype
                break
        if found_model:
            break
    
    if not found_model:
        print(f"\n❌ Error: Model '{model_name}' not found in downloaded models")
        print(f"\nUse 'airunner-hf-download --downloaded' to see downloaded models")
        return False
    
    model_path = found_model["path"]
    size_gb = found_model["size_gb"]
    
    # Show model details
    print(f"\n⚠️  About to delete: {found_model['name']}")
    print(f"   Type: {found_type}")
    print(f"   Size: {size_gb:.1f}GB")
    print(f"   Path: {model_path}")
    
    # Confirm deletion (unless force flag is set)
    if not force:
        response = input(f"\nAre you sure you want to delete this model? [y/N]: ").strip().lower()
        if response != 'y':
            print("Deletion cancelled.")
            return False
    else:
        print("\n(Force mode: skipping confirmation)")
    
    try:
        shutil.rmtree(model_path)
        print(f"\n✅ Successfully deleted: {found_model['name']} ({size_gb:.1f}GB freed)")
        return True
    except Exception as e:
        print(f"\n❌ Error deleting model: {e}")
        return False


def main():
    """Main entry point for airunner-hf-download."""
    parser = argparse.ArgumentParser(
        description="Download HuggingFace models for AI Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "model",
        nargs="?",
        default=None,
        help="Model key (e.g., 'qwen3-8b') or repo_id (e.g., 'Qwen/Qwen3-8B'). "
             "If omitted, lists available models.",
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["llm", "art", "tts", "stt", "embedding"],
        default=None,
        help="Filter model list by type, or specify type for arbitrary repo download",
    )
    
    parser.add_argument(
        "--full", "-f",
        action="store_true",
        help="Download full safetensors model instead of GGUF (larger but higher precision)",
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Override output directory",
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available models (same as running without arguments)",
    )
    
    parser.add_argument(
        "--downloaded", "-d",
        action="store_true",
        help="List downloaded models",
    )
    
    parser.add_argument(
        "--delete",
        type=str,
        metavar="MODEL",
        help="Delete a downloaded model by name",
    )
    
    parser.add_argument(
        "--force", "-y",
        action="store_true",
        help="Skip confirmation prompt when deleting (use with --delete)",
    )
    
    args = parser.parse_args()
    
    # Handle --delete
    if args.delete:
        success = delete_model(args.delete, force=args.force)
        return 0 if success else 1
    
    # Handle --downloaded
    if args.downloaded:
        downloaded = get_downloaded_models()
        print_downloaded_models(downloaded, args.type)
        return 0
    
    # Get all available models
    models = get_all_available_models()
    
    # List models if no model specified or --list flag
    if args.model is None or args.model == "list" or args.list:
        print_model_list(models, args.type)
        return 0
    
    # Try to find the model in our catalog
    model_info = find_model(args.model, models)
    
    if model_info:
        # Found in catalog - download it
        # Default to GGUF unless --full flag is used
        use_gguf = not args.full
        success = download_model(model_info, use_gguf=use_gguf, output_dir=args.output)
        return 0 if success else 1
    
    # Not in catalog - check if it looks like a repo_id
    if "/" in args.model:
        print(f"\n⚠️  Model '{args.model}' not in catalog, downloading as custom repository...")
        model_type = args.type or "llm"
        success = download_arbitrary_repo(args.model, model_type)
        return 0 if success else 1
    
    # Model not found
    print(f"\n❌ Error: Model '{args.model}' not found in catalog")
    print(f"\nAvailable model keys:")
    for mtype, mlist in models.items():
        if mlist:
            keys = [m["key"] for m in mlist[:5]]
            print(f"  {mtype}: {', '.join(keys)}{'...' if len(mlist) > 5 else ''}")
    print(f"\nUse 'airunner-hf-download' to see full list")
    print(f"Or specify a full repo_id like 'user/model-name'")
    return 1


if __name__ == "__main__":
    sys.exit(main())
