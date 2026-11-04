from typing import Optional

__all__ = ['__version__', 'debug', 'cuda', 'git_version', 'hip', 'rocm', 'xpu']
__version__ = '2.13.0+cu129'
debug = False
cuda: Optional[str] = '12.9'
git_version = 'cf30153c4c131c8164ee7798e5022d810682e2cb'
hip: Optional[str] = None
rocm: Optional[str] = None
xpu: Optional[str] = None
