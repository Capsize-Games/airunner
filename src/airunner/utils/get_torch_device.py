import torch


def get_torch_device(card_index: int = 0):
    use_cuda = torch.cuda.is_available()
    return torch.device(f"cuda:{card_index}" if use_cuda else "cpu")
