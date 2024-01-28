import os

BASE_PATH = os.path.join(os.path.expanduser("~"), ".airunner")
SQLITE_DB_NAME = "airunner.db"
SQLITE_DB_PATH = os.path.join(BASE_PATH, SQLITE_DB_NAME)
CONTROLNET_OPTIONS = [
    "Canny",
    "MLSD",
    "Depth Leres",
    "Depth Leres++",
    "Depth Midas",
    # "Depth Zoe",
    "Normal Bae",
    # "Normal Midas",
    # "Segmentation",
    "Lineart Anime",
    "Lineart Coarse",
    "Lineart Realistic",
    "Openpose",
    "Openpose Face",
    "Openpose Faceonly",
    "Openpose Full",
    "Openpose Hand",
    "Scribble Hed",
    "Scribble Pidinet",
    "Softedge Hed",
    "Softedge Hedsafe",
    "Softedge Pidinet",
    "Softedge Pidsafe",
    # "Pixel2Pixel",
    # "Inpaint",
    "Shuffle",
]
DEFAULT_PATHS = {
    "art": {
        "models": {
            "txt2img": os.path.join(BASE_PATH, "art", "models", "txt2img"),
            "depth2img": os.path.join(BASE_PATH, "art", "models", "depth2img"),
            "pix2pix": os.path.join(BASE_PATH, "art", "models", "pix2pix"),
            "inpaint": os.path.join(BASE_PATH, "art", "models", "inpaint"),
            "upscale": os.path.join(BASE_PATH, "art", "models", "upscale"),
            "txt2vid": os.path.join(BASE_PATH, "art", "models", "txt2vid"),
            "embeddings": os.path.join(BASE_PATH, "art", "models", "embeddings"),
            "lora": os.path.join(BASE_PATH, "art", "models", "lora"),
            "vae": os.path.join(BASE_PATH, "art", "models", "vae"),
        },
        "other": {
            "images": os.path.join(BASE_PATH, "art", "other", "images"),
            "videos": os.path.join(BASE_PATH, "art", "other", "videos"),
        },
    },
    "text": {
        "models": {
            "casuallm": os.path.join(BASE_PATH, "text", "models", "casuallm"),
            "seq2seq": os.path.join(BASE_PATH, "text", "models", "seq2seq"),
            "visualqa": os.path.join(BASE_PATH, "text", "models", "visualqa"),
        },
        "other": {
            "ebooks": os.path.join(BASE_PATH, "text", "other", "ebooks"),
            "documents": os.path.join(BASE_PATH, "text", "other", "documents"),
        }
    }
}