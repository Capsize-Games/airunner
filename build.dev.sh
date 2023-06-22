./venv/bin/python -m PyInstaller --log-level=INFO --noconfirm  ./build.airunner.linux.dev.spec
cp -R ./venv/lib/python3.10/site-packages/timm ./dist/airunner/
cp ./venv/lib/python3.10/site-packages/torch/lib/libtorch_cuda_linalg.so ./dist/airunner/
cp -R ./venv/lib/python3.10/site-packages/Pillow-9.5.0.dist-info ./dist/airunner/