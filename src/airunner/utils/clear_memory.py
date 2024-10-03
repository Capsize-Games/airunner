import gc
import os

import psutil
import torch

def print_gpu_memory_usage():
    allocated = torch.cuda.memory_allocated(0) / 1024**2
    reserved = torch.cuda.memory_reserved(0) / 1024**2
    print(f"Allocated GPU memory: {allocated:.2f} MB")
    print(f"Reserved GPU memory: {reserved:.2f} MB")

def print_cpu_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    rss = memory_info.rss / 1024**2  # Resident Set Size
    vms = memory_info.vms / 1024**2  # Virtual Memory Size
    print(f"RSS (Resident Set Size): {rss:.2f} MB")
    print(f"VMS (Virtual Memory Size): {vms:.2f} MB")

def clear_memory(device=0):
    """
    Clear the GPU ram.
    """
    if torch.cuda.is_available():
        try:
            torch.cuda.set_device(device)
            torch.cuda.empty_cache()
            torch.cuda.reset_max_memory_allocated(device=device)
            torch.cuda.reset_max_memory_cached(device=device)
            torch.cuda.synchronize(device=device)
        except RuntimeError:
            print("Failed to clear memory")
    gc.collect()
