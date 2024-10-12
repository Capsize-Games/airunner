import torch


def get_torch_device(card_index: int = 0):
    use_cuda = torch.cuda.is_available()
    if not use_cuda:
        print("WARNING: CUDA NOT AVAILABLE, USING CPU")
    return torch.device(f"cuda:{card_index}" if use_cuda else "cpu")
