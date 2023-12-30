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