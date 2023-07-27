./venv/bin/python -m PyInstaller --log-level=INFO --noconfirm  ./build.airunner-socket-server.linux.dev.spec
cp -R ./venv/lib/python3.10/site-packages/timm ./dist/airunner-socket-server/
cp ./venv/lib/python3.10/site-packages/torch/lib/libtorch_cuda_linalg.so ./dist/airunner-socket-server/
cp -R ./venv/lib/python3.10/site-packages/Pillow-9.5.0.dist-info ./dist/airunner-socket-server/

# remove redundant files
rm -rf ./dist/airunner-socket-server/nvfuser
rm -rf ./dist/airunner-socket-server/functorch
rm -rf ./dist/airunner-socket-server/pydantic
rm -rf ./dist/airunner-socket-server/tensorflow/python/data/experimental
rm -f ./dist/airunner-socket-server/matplotlib/_qhull.cpython-310-x86_64-linux-gnu.so
rm -f ./dist/airunner-socket-server/JIT/_C.so
rm -f ./dist/airunner-socket-server/libtorch_cuda_linalg.so
rm -f ./dist/airunner-socket-server/libtorch.so
rm -f ./dist/airunner-socket-server/libtorch_cuda.so
rm -f ./dist/airunner-socket-server/libnvfuser_codegen.so
rm -f ./dist/airunner-socket-server/libc10_cuda.so
rm -f ./dist/airunner-socket-server/libtorch_python.so
rm -f ./dist/airunner-socket-server/libtorch_cpu.so
rm -f ./dist/airunner-socket-server/libc10.so
rm -f ./dist/airunner-socket-server/libshm.so