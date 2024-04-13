import os
import threading

lock = threading.Lock()


def delete_image(path):
    with lock:
        if os.path.exists(path):
            os.remove(path)


